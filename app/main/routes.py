from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from app import db
from app.main import bp
from app.models import Ticket, TicketStatus, TicketPriority, TicketType, User, TimeEntry, Asset, KnowledgeBaseArticle, TicketComment, Role, Setting
from app.main.forms import TicketForm, TicketCommentForm, TicketAssignForm, TicketStatusForm, UserForm, SettingsForm, CommentReplyForm
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from functools import wraps
import logging

# Role-based permission decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.role or current_user.role.name != 'Administrator':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    """Requires user to be Administrator or Technician"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.role or current_user.role.name not in ['Administrator', 'Technician']:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def technician_or_admin_required(f):
    """Requires user to be Administrator or Technician"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.role or current_user.role.name not in ['Administrator', 'Technician']:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to check if a user owns a ticket or is staff
def can_view_ticket(ticket):
    if not current_user.role:
        return False
    if current_user.role.name in ['Administrator', 'Technician']:
        return True
    return ticket.created_by == current_user.id

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
        # If user role, only count tickets created by this user
        if current_user.role and current_user.role.name == 'User':
            count = Ticket.query.filter_by(status_id=status.id, created_by=current_user.id).count()
        else:
            count = Ticket.query.filter_by(status_id=status.id).count()
        status_counts[status.name] = {
            'count': count,
            'color': status.color
        }
    
    # Get ticket counts by priority
    priorities = TicketPriority.query.all()
    priority_counts = {}
    for priority in priorities:
        # If user role, only count tickets created by this user
        if current_user.role and current_user.role.name == 'User':
            count = Ticket.query.filter_by(priority_id=priority.id, created_by=current_user.id).count()
        else:
            count = Ticket.query.filter_by(priority_id=priority.id).count()
        priority_counts[priority.name] = {
            'count': count,
            'color': priority.color
        }
    
    # Get open tickets assigned to or created by current user
    if current_user.role and current_user.role.name == 'User':
        # For users, show tickets they created
        my_tickets = Ticket.query.join(TicketStatus).filter(
            Ticket.created_by == current_user.id,
            TicketStatus.is_closed == False
        ).order_by(Ticket.created_at.desc()).limit(5).all()
    else:
        # For staff, show tickets assigned to them
        my_tickets = Ticket.query.join(TicketStatus).filter(
            Ticket.assigned_to == current_user.id,
            TicketStatus.is_closed == False
        ).order_by(Ticket.created_at.desc()).limit(5).all()
    
    # Get recent tickets
    if current_user.role and current_user.role.name == 'User':
        # For users, only show tickets they created
        recent_tickets = Ticket.query.filter_by(created_by=current_user.id).order_by(Ticket.created_at.desc()).limit(10).all()
        # Users don't see unassigned tickets
        unassigned_tickets = []
    else:
        # For staff, show all tickets
        recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(10).all()
        # For technicians and administrators, show unassigned tickets
        unassigned_tickets = Ticket.query.join(TicketStatus).filter(
            Ticket.assigned_to == None,
            TicketStatus.is_closed == False
        ).order_by(Ticket.created_at.desc()).limit(5).all()
    
    # Get overdue tickets
    if current_user.role and current_user.role.name == 'User':
        # For users, only count their tickets
        overdue_tickets = Ticket.query.filter(
            Ticket.due_date < datetime.utcnow(),
            Ticket.status.has(TicketStatus.is_closed == False),
            Ticket.created_by == current_user.id
        ).count()
    else:
        # For staff, count all tickets
        overdue_tickets = Ticket.query.filter(
            Ticket.due_date < datetime.utcnow(),
            Ticket.status.has(TicketStatus.is_closed == False)
        ).count()
    
    # Get SLA breached tickets
    if current_user.role and current_user.role.name == 'User':
        # For users, only count their tickets
        sla_breached = Ticket.query.filter(
            and_(
                Ticket.status.has(TicketStatus.is_closed == False),
                Ticket.created_by == current_user.id,
                (
                    and_(Ticket.sla_response_due < datetime.utcnow(), Ticket.sla_response_met == False) |
                    and_(Ticket.sla_resolution_due < datetime.utcnow(), Ticket.sla_resolution_met == False)
                )
            )
        ).count()
    else:
        # For staff, count all tickets
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
                           unassigned_tickets=unassigned_tickets,
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
        if form.assigned_to.data != 0 and current_user.role.name in ['Administrator', 'Technician']:  # Not unassigned and user has permission
            ticket.assigned_to = form.assigned_to.data
        else:
            ticket.assigned_to = None  # Ensure regular users can't assign tickets
            
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
    
    # Check if user has permission to view this ticket
    if not can_view_ticket(ticket):
        flash('You do not have permission to view this ticket.', 'danger')
        return redirect(url_for('main.dashboard'))
    
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
        query = TicketComment.query.filter_by(ticket_id=ticket_id, parent_id=None)
        # If user is not staff, only show public comments
        if current_user.role.name not in ['Administrator', 'Technician']:
            query = query.filter_by(is_internal=False)
        comments = query.order_by(TicketComment.created_at.desc()).all()
    else:
        query = TicketComment.query.filter_by(ticket_id=ticket_id, parent_id=None)
        # If user is not staff, only show public comments
        if current_user.role.name not in ['Administrator', 'Technician']:
            query = query.filter_by(is_internal=False)
        comments = query.order_by(TicketComment.created_at).all()
        
    # Fetch replies for each comment
    for comment in comments:
        # If user is not staff, only show public replies
        if current_user.role.name not in ['Administrator', 'Technician']:
            comment.replies = TicketComment.query.filter_by(
                ticket_id=ticket_id, 
                parent_id=comment.id,
                is_internal=False
            ).order_by(TicketComment.created_at).all()
        else:
            comment.replies = TicketComment.query.filter_by(
                ticket_id=ticket_id, 
                parent_id=comment.id
            ).order_by(TicketComment.created_at).all()
        
    # Create a reply form for each comment
    reply_form = CommentReplyForm()
    
    # Set the current assignee in the form
    if ticket.assigned_to:
        assign_form.assigned_to.data = ticket.assigned_to
    else:
        assign_form.assigned_to.data = 0
    
    # Set the current status in the form
    if ticket.status_id:
        status_form.status_id.data = ticket.status_id
        
    # Determine if user can modify ticket status and assignment
    can_modify = current_user.role.name in ['Administrator', 'Technician']
    
    # Determine if user can add internal comments
    can_add_internal = current_user.role.name in ['Administrator', 'Technician']
    
    return render_template('main/view_ticket.html', 
                           title=f'Ticket #{ticket.id}', 
                           ticket=ticket, 
                           comment_form=comment_form,
                           reply_form=reply_form,
                           assign_form=assign_form,
                           status_form=status_form,
                           comments=comments,
                           sort_order=sort_order,
                           active_tab=active_tab,
                           can_modify=can_modify,
                           can_add_internal=can_add_internal)

@bp.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
@login_required
@staff_required
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
@staff_required
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
    ticket = Ticket.query.get_or_404(ticket_id)
    form = TicketCommentForm()
    
    current_app.logger.info(f'Attempting to add comment to ticket {ticket_id} by user {current_user.id}')
    current_app.logger.debug(f'Form data received: {request.form}')
    
    # Check if user has permission to view this ticket
    if not can_view_ticket(ticket):
        current_app.logger.warning(f'User {current_user.id} lacks permission to comment on ticket {ticket_id}')
        flash('You do not have permission to comment on this ticket.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if form.validate_on_submit():
        current_app.logger.info(f'Comment form validated successfully for ticket {ticket_id}')
        try:
            # The is_internal field is a SelectField with string values
            is_internal = form.is_internal.data == '1'
            current_app.logger.debug(f'is_internal value determined: {is_internal}')
            
            if is_internal and current_user.role.name not in ['Administrator', 'Technician']:
                current_app.logger.warning(f'User {current_user.id} attempted to add internal comment without permission on ticket {ticket_id}')
                flash('You do not have permission to add internal comments.', 'danger')
                return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))
            
            # Create new comment object
            comment = TicketComment(
                ticket_id=ticket_id,
                user_id=current_user.id,
                content=form.content.data,
                is_internal=is_internal,
                created_at=datetime.utcnow()
            )
            current_app.logger.debug(f'TicketComment object created: {comment}')
            
            db.session.add(comment)
            current_app.logger.info(f'Adding comment {comment.id if comment.id else "(pending)"} to session for ticket {ticket_id}')
            db.session.flush()  # Get the comment ID before checking status
            current_app.logger.info(f'Comment {comment.id} flushed to session.')
            
            # Check if status is being updated and user has permission
            status_id = form.status_id.data
            current_app.logger.debug(f'Status ID from form: {status_id}')
            if status_id != 0 and current_user.role and current_user.role.name in ['Administrator', 'Technician']:
                current_app.logger.info(f'Updating ticket {ticket_id} status to {status_id}')
                # Update ticket status
                ticket.status_id = status_id
                db.session.add(ticket) # Ensure ticket update is staged
                flash('Comment added and ticket status updated successfully!', 'success')
            else:
                flash('Comment added successfully!', 'success')
            
            current_app.logger.info(f'Committing transaction for comment {comment.id} on ticket {ticket_id}')
            db.session.commit()
            current_app.logger.info(f'Transaction committed successfully for comment {comment.id}')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error adding comment to ticket {ticket_id}: {str(e)}', exc_info=True)
            flash('Error adding comment. Please check logs for details.', 'danger')
    else:
        # Log validation errors if the form fails validation
        current_app.logger.warning(f'Comment form validation failed for ticket {ticket_id}. Errors: {form.errors}')
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in field '{getattr(form, field).label.text}': {error}", 'danger')
    
    return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))

@bp.route('/tickets/<int:ticket_id>/comment/<int:comment_id>/reply/form', methods=['GET'])
@login_required
def reply_to_comment_form(ticket_id, comment_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    parent_comment = TicketComment.query.get_or_404(comment_id)
    form = CommentReplyForm()
    
    # Check if user has permission to view this ticket
    if not can_view_ticket(ticket):
        flash('You do not have permission to comment on this ticket.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Verify that the parent comment belongs to the ticket
    if parent_comment.ticket_id != ticket_id:
        flash('Invalid comment.', 'danger')
        return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))
    
    return render_template('main/reply_to_comment.html', 
                          title=f'Reply to Comment - Ticket #{ticket.id}',
                          ticket=ticket,
                          parent_comment=parent_comment,
                          form=form,
                          can_add_internal=current_user.role.name in ['Administrator', 'Technician'])

@bp.route('/tickets/<int:ticket_id>/comment/<int:comment_id>/reply', methods=['POST'])
@login_required
def reply_to_comment(ticket_id, comment_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    parent_comment = TicketComment.query.get_or_404(comment_id)
    form = CommentReplyForm()
    
    # Check if user has permission to view this ticket
    if not can_view_ticket(ticket):
        flash('You do not have permission to comment on this ticket.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Verify that the parent comment belongs to the ticket
    if parent_comment.ticket_id != ticket_id:
        flash('Invalid comment.', 'danger')
        return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))
    
    if form.validate_on_submit():
        try:
            is_internal = form.is_internal.data == '1'
            current_app.logger.debug(f'Reply is_internal value determined: {is_internal}')

            if is_internal and current_user.role.name not in ['Administrator', 'Technician']:
                current_app.logger.warning(f'User {current_user.id} attempted to add internal reply without permission on ticket {ticket_id}, comment {comment_id}')
                flash('You do not have permission to add internal comments.', 'danger')
                return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments'))

            # Create new reply comment object
            reply = TicketComment(
                ticket_id=ticket_id,
                user_id=current_user.id,
                content=form.content.data,
                is_internal=is_internal,
                parent_id=comment_id,
                created_at=datetime.utcnow()
            )
            current_app.logger.debug(f'TicketComment reply object created: {reply}')

            db.session.add(reply)
            current_app.logger.info(f'Adding reply {reply.id if reply.id else "(pending)"} to session for ticket {ticket_id}')
            db.session.commit()
            current_app.logger.info(f'Transaction committed successfully for reply {reply.id}')

            flash('Reply added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error adding reply to comment {comment_id} on ticket {ticket_id}: {str(e)}', exc_info=True)
            flash('Error adding reply. Please check logs for details.', 'danger')
    else:
        # Log validation errors if the form fails validation
        current_app.logger.warning(f'Reply form validation failed for ticket {ticket_id}, comment {comment_id}. Errors: {form.errors}')
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in field '{getattr(form, field).label.text}': {error}", 'danger')

    # Redirect to the specific comment that was replied to
    return redirect(url_for('main.view_ticket', ticket_id=ticket_id, tab='comments') + f'#comment-{comment_id}')

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
    form = UserForm(original_username=user.username, original_email=user.email)
    
    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role.name if user.role else 'User'  # Set to role name, not role object
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

@bp.route('/settings')
@login_required
@admin_required
def settings():
    # Redirect to the new settings module
    return redirect(url_for('settings.index'))

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
