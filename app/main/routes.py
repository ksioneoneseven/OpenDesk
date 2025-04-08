from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from app import db
from app.main import bp
from app.models import Ticket, TicketStatus, TicketPriority, TicketType, User, TimeEntry, Asset, KnowledgeBaseArticle, TicketComment, Role, Setting
from app.main.forms import TicketForm, TicketCommentForm, TicketAssignForm, TicketStatusForm, UserForm, SettingsForm
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from functools import wraps

# Helper function to check if a user is an administrator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.role or current_user.role.name != 'Administrator':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

@bp.route('/dashboard')
@login_required
def dashboard():
    # Get ticket counts by status
    statuses = TicketStatus.query.all()
    status_counts = {}
    for status in statuses:
        count = Ticket.query.filter_by(status_id=status.id).count()
        status_counts[status.name] = {
            'count': count,
            'color': status.color
        }
    
    # Get ticket counts by priority
    priorities = TicketPriority.query.all()
    priority_counts = {}
    for priority in priorities:
        count = Ticket.query.filter_by(priority_id=priority.id).count()
        priority_counts[priority.name] = {
            'count': count,
            'color': priority.color
        }
    
    # Get open tickets assigned to current user
    my_tickets = Ticket.query.join(TicketStatus).filter(
        Ticket.assigned_to == current_user.id,
        TicketStatus.is_closed == False
    ).order_by(Ticket.created_at.desc()).limit(5).all()
    
    # Get recent tickets
    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(10).all()
    
    # Get overdue tickets
    overdue_tickets = Ticket.query.filter(
        Ticket.due_date < datetime.utcnow(),
        Ticket.status.has(TicketStatus.is_closed == False)
    ).count()
    
    # Get SLA breached tickets
    sla_breached = Ticket.query.filter(
        and_(
            Ticket.status.has(TicketStatus.is_closed == False),
            (
                and_(Ticket.sla_response_due < datetime.utcnow(), Ticket.sla_response_met == False) |
                and_(Ticket.sla_resolution_due < datetime.utcnow(), Ticket.sla_resolution_met == False)
            )
        )
    ).count()
    
    # Get SLA at risk tickets (within 75% of SLA time)
    now = datetime.utcnow()
    at_risk_tickets = Ticket.query.filter(
        and_(
            Ticket.status.has(TicketStatus.is_closed == False),
            (
                and_(
                    Ticket.sla_response_met == False,
                    Ticket.sla_response_due > now,
                    Ticket.sla_response_due < now + timedelta(hours=4)
                ) |
                and_(
                    Ticket.sla_resolution_met == False,
                    Ticket.sla_resolution_due > now,
                    Ticket.sla_resolution_due < now + timedelta(hours=8)
                )
            )
        )
    ).count()
    
    # Get ticket volume over time (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_tickets = db.session.query(
        func.date(Ticket.created_at).label('date'),
        func.count(Ticket.id).label('count')
    ).filter(Ticket.created_at >= seven_days_ago).group_by(func.date(Ticket.created_at)).all()
    
    daily_ticket_data = {
        'labels': [str(day.date) for day in daily_tickets],
        'counts': [day.count for day in daily_tickets]
    }
    
    # Get agent performance metrics
    agents = User.query.join(User.role).filter(User.role.has(name='Agent')).all()
    agent_metrics = []
    
    for agent in agents:
        closed_tickets = Ticket.query.filter(
            Ticket.assigned_to == agent.id,
            Ticket.status.has(TicketStatus.is_closed == True)
        ).count()
        
        total_time = db.session.query(func.sum(TimeEntry.duration)).filter(
            TimeEntry.user_id == agent.id
        ).scalar() or 0
        
        agent_metrics.append({
            'name': agent.full_name,
            'closed_tickets': closed_tickets,
            'total_time': total_time
        })
    
    # Get asset statistics
    total_assets = Asset.query.count()
    assigned_assets = Asset.query.filter(Asset.assigned_to_id != None).count()
    
    # Get knowledge base statistics
    kb_articles = KnowledgeBaseArticle.query.filter_by(is_published=True).count()
    
    return render_template('main/dashboard.html', 
                           title='Dashboard',
                           status_counts=status_counts,
                           priority_counts=priority_counts,
                           my_tickets=my_tickets,
                           recent_tickets=recent_tickets,
                           overdue_tickets=overdue_tickets,
                           sla_breached=sla_breached,
                           at_risk_tickets=at_risk_tickets,
                           daily_ticket_data=daily_ticket_data,
                           agent_metrics=agent_metrics,
                           total_assets=total_assets,
                           assigned_assets=assigned_assets,
                           kb_articles=kb_articles)

@bp.route('/tickets')
@login_required
def tickets():
    # Get all tickets
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    return render_template('main/tickets.html', title='All Tickets', tickets=tickets)

@bp.route('/tickets/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    form = TicketForm()
    
    if form.validate_on_submit():
        ticket = Ticket(
            subject=form.subject.data,
            description=form.description.data,
            requester_name=form.requester_name.data,
            requester_email=form.requester_email.data,
            status_id=form.status_id.data,
            priority_id=form.priority_id.data,
            type_id=form.type_id.data,
            created_by=current_user.id
        )
        
        # Handle assigned_to field
        if form.assigned_to.data != 0:  # Not unassigned
            ticket.assigned_to = form.assigned_to.data
            
        # Handle due date
        if form.due_date.data:
            ticket.due_date = form.due_date.data
            
        db.session.add(ticket)
        db.session.commit()
        
        flash('Ticket created successfully!', 'success')
        return redirect(url_for('main.view_ticket', ticket_id=ticket.id))
    
    return render_template('main/create_ticket.html', title='Create Ticket', form=form)

@bp.route('/tickets/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    comment_form = TicketCommentForm()
    assign_form = TicketAssignForm()
    status_form = TicketStatusForm()
    
    # Get active tab from query parameter
    active_tab = request.args.get('tab', 'details')
    
    # Get comment sort order from query parameter or session
    sort_order = request.args.get('sort', '')
    if sort_order not in ['asc', 'desc']:
        # If not specified in URL, try to get from session
        sort_order = session.get('comment_sort_order', 'asc')
    else:
        # Save to session for future requests
        session['comment_sort_order'] = sort_order
        # If sort order is specified, set active tab to comments
        active_tab = 'comments'
    
    # Query comments with the appropriate sort order
    if sort_order == 'desc':
        comments = TicketComment.query.filter_by(ticket_id=ticket_id).order_by(TicketComment.created_at.desc()).all()
    else:
        comments = TicketComment.query.filter_by(ticket_id=ticket_id).order_by(TicketComment.created_at).all()
    
    # Set the current assignee in the form
    if ticket.assigned_to:
        assign_form.assigned_to.data = ticket.assigned_to
    else:
        assign_form.assigned_to.data = 0
    
    # Set the current status in the form
    if ticket.status_id:
        status_form.status_id.data = ticket.status_id
    
    return render_template('main/view_ticket.html', 
                           title=f'Ticket #{ticket.id}', 
                           ticket=ticket, 
                           comment_form=comment_form,
                           assign_form=assign_form,
                           status_form=status_form,
                           comments=comments,
                           sort_order=sort_order,
                           active_tab=active_tab)

@bp.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    form = TicketAssignForm()
    
    if form.validate_on_submit():
        try:
            # If assigned_to is 0, set it to None (unassigned)
            if form.assigned_to.data == 0:
                ticket.assigned_to = None
                flash('Ticket unassigned successfully!', 'success')
            else:
                # Check if the user exists
                user = User.query.get(form.assigned_to.data)
                if user:
                    ticket.assigned_to = user.id
                    flash(f'Ticket assigned to {user.username} successfully!', 'success')
                else:
                    flash('Invalid user selected!', 'danger')
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error assigning ticket: {str(e)}')
            flash('Error assigning ticket. Please try again.', 'danger')
    
    return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))

@bp.route('/tickets/<int:ticket_id>/status', methods=['POST'])
@login_required
def update_ticket_status(ticket_id):
    form = TicketStatusForm()
    
    if form.validate_on_submit():
        try:
            # Use direct SQL to update the ticket status
            from sqlalchemy import text
            
            # Get the status information first
            status = TicketStatus.query.get(form.status_id.data)
            if not status:
                flash('Invalid status selected!', 'danger')
                return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))
            
            # Get the current status name for the comment
            ticket = Ticket.query.get_or_404(ticket_id)
            old_status = ticket.status.name if ticket.status else 'None'
            
            # Determine if we need to update SLA metrics
            update_resolved = False
            update_sla_met = False
            current_time = datetime.utcnow()
            
            if status.name.lower() in ['resolved', 'closed', 'completed']:
                update_resolved = True
                if ticket.sla_resolution_due and current_time <= ticket.sla_resolution_due:
                    update_sla_met = True
            
            # Update the ticket status
            update_sql = text("""
                UPDATE ticket 
                SET status_id = :status_id,
                    resolved_at = CASE WHEN :update_resolved THEN :current_time ELSE resolved_at END,
                    sla_resolution_met = CASE WHEN :update_sla_met THEN 1 ELSE sla_resolution_met END
                WHERE id = :ticket_id
            """)
            
            # Add a system comment about the status change
            comment_sql = text("""
                INSERT INTO ticket_comment (ticket_id, user_id, content, is_internal, created_at)
                VALUES (:ticket_id, :user_id, :content, :is_internal, :created_at)
            """)
            
            # Execute both operations in a transaction
            with db.engine.begin() as conn:
                # Update the ticket
                conn.execute(update_sql, {
                    'status_id': status.id,
                    'update_resolved': update_resolved,
                    'current_time': current_time,
                    'update_sla_met': update_sla_met,
                    'ticket_id': ticket_id
                })
                
                # Add the comment
                conn.execute(comment_sql, {
                    'ticket_id': ticket_id,
                    'user_id': current_user.id,
                    'content': f'Status changed from {old_status} to {status.name}',
                    'is_internal': True,
                    'created_at': current_time
                })
            
            flash(f'Ticket status updated to {status.name}!', 'success')
        except Exception as e:
            current_app.logger.error(f'Error updating ticket status: {str(e)}')
            flash('Error updating ticket status. Please try again.', 'danger')
    
    return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))

@bp.route('/tickets/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    form = TicketCommentForm()
    
    if form.validate_on_submit():
        try:
            # Use the direct SQL execution approach
            from sqlalchemy import text
            
            # Insert the comment directly using SQL
            sql = text("""
                INSERT INTO ticket_comment (ticket_id, user_id, content, is_internal, created_at)
                VALUES (:ticket_id, :user_id, :content, :is_internal, :created_at)
            """)
            
            # Execute the SQL with parameters
            with db.engine.begin() as conn:
                conn.execute(sql, {
                    'ticket_id': ticket_id,
                    'user_id': current_user.id,
                    'content': form.content.data,
                    'is_internal': form.is_internal.data,
                    'created_at': datetime.utcnow()
                })
            
            flash('Comment added successfully!', 'success')
        except Exception as e:
            current_app.logger.error(f'Error adding comment: {str(e)}')
            flash('Error adding comment. Please try again.', 'danger')
    
    return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))

@bp.route('/users')
@login_required
@admin_required
def users():
    # Get all users
    users = User.query.order_by(User.username).all()
    return render_template('main/users.html', title='User Administration', users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    form = UserForm()
    if form.validate_on_submit():
        try:
            # Get role by name
            role = Role.query.filter_by(name=form.role.data).first()
            if not role:
                # Create the role if it doesn't exist
                role = Role(name=form.role.data, description=f'{form.role.data} role')
                db.session.add(role)
                
            user = User(username=form.username.data,
                       email=form.email.data,
                       role=role,
                       is_active=bool(form.is_active.data))
            
            if form.password.data:
                user.set_password(form.password.data)
                
            db.session.add(user)
            db.session.commit()
            flash('User created successfully!', 'success')
            return redirect(url_for('main.users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating user: {str(e)}')
            flash('Error creating user. Please try again.', 'danger')
    
    return render_template('main/edit_user.html', title='Create User', form=form, user=None)

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(original_username=user.username)
    
    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role
        form.is_active.data = user.is_active
    
    if form.validate_on_submit():
        try:
            user.username = form.username.data
            user.email = form.email.data
            
            # Get role by name
            role = Role.query.filter_by(name=form.role.data).first()
            if not role:
                # Create the role if it doesn't exist
                role = Role(name=form.role.data, description=f'{form.role.data} role')
                db.session.add(role)
            
            user.role = role
            user.is_active = bool(form.is_active.data)
            
            if form.password.data:
                user.set_password(form.password.data)
                
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('main.users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error updating user: {str(e)}')
            flash('Error updating user. Please try again.', 'danger')
    
    return render_template('main/edit_user.html', title='Edit User', form=form, user=user)

@bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    try:
        # Don't allow deactivating yourself
        if user.id == current_user.id:
            flash('You cannot deactivate your own account!', 'danger')
            return redirect(url_for('main.users'))
            
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User {user.username} has been {status}!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error toggling user status: {str(e)}')
        flash('Error updating user status. Please try again.', 'danger')
    
    return redirect(url_for('main.users'))

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    form = SettingsForm()
    
    # Get current theme setting
    theme_setting = Setting.query.filter_by(key='theme').first()
    
    if form.validate_on_submit():
        try:
            # If theme setting exists, update it
            if theme_setting:
                theme_setting.value = form.theme.data
            else:
                # Create new theme setting
                theme_setting = Setting(key='theme', value=form.theme.data, description='Application theme (light/dark)')
                db.session.add(theme_setting)
            
            db.session.commit()
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('main.settings'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating settings: {str(e)}', 'danger')
    
    # Set form defaults from current settings
    if theme_setting and not form.is_submitted():
        form.theme.data = theme_setting.value
    elif not theme_setting and not form.is_submitted():
        form.theme.data = 'light'  # Default to light mode if no setting exists
    
    return render_template('main/settings.html', title='Application Settings', form=form)

@bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.dashboard'))
    
    # Search tickets
    tickets = Ticket.query.filter(
        (Ticket.subject.contains(query)) |
        (Ticket.description.contains(query)) |
        (Ticket.requester_email.contains(query)) |
        (Ticket.requester_name.contains(query))
    ).limit(20).all()
    
    # Search knowledge base
    kb_articles = KnowledgeBaseArticle.query.filter(
        (KnowledgeBaseArticle.title.contains(query)) |
        (KnowledgeBaseArticle.content.contains(query))
    ).filter_by(is_published=True).limit(10).all()
    
    # Search assets
    assets = Asset.query.filter(
        (Asset.name.contains(query)) |
        (Asset.serial_number.contains(query)) |
        (Asset.notes.contains(query))
    ).limit(10).all()
    
    return render_template('main/search_results.html',
                           title='Search Results',
                           query=query,
                           tickets=tickets,
                           kb_articles=kb_articles,
                           assets=assets)
