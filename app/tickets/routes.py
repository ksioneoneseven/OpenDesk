from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.tickets import bp
from app.tickets.forms import TicketForm, TicketCommentForm, TimeEntryForm, ManualTimeEntryForm, TicketFilterForm
from app.models import Ticket, TicketComment, TicketStatus, TicketPriority, TicketType, User, TimeEntry, Asset
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

@bp.route('/')
@login_required
def index():
    form = TicketFilterForm()
    
    # Get filter parameters
    status_id = request.args.get('status', type=int, default=0)
    priority_id = request.args.get('priority', type=int, default=0)
    assigned_to = request.args.get('assigned_to', type=int, default=0)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    
    # Base query
    query = Ticket.query
    
    # Apply filters
    if status_id > 0:
        query = query.filter(Ticket.status_id == status_id)
    
    if priority_id > 0:
        query = query.filter(Ticket.priority_id == priority_id)
    
    if assigned_to > 0:
        query = query.filter(Ticket.assigned_to == assigned_to)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Ticket.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)  # Include the entire day
            query = query.filter(Ticket.created_at <= to_date)
        except ValueError:
            pass
    
    # Get tickets
    tickets = query.order_by(Ticket.created_at.desc()).all()
    
    # Get counts for sidebar
    all_tickets_count = Ticket.query.count()
    open_tickets_count = Ticket.query.join(TicketStatus).filter(TicketStatus.is_closed == False).count()
    my_tickets_count = Ticket.query.filter(Ticket.assigned_to == current_user.id).count()
    unassigned_tickets_count = Ticket.query.filter(Ticket.assigned_to == None).count()
    
    # Get SLA breached tickets
    sla_breached_count = Ticket.query.filter(
        and_(
            Ticket.status.has(TicketStatus.is_closed == False),
            or_(
                and_(Ticket.sla_response_due < datetime.utcnow(), Ticket.sla_response_met == False),
                and_(Ticket.sla_resolution_due < datetime.utcnow(), Ticket.sla_resolution_met == False)
            )
        )
    ).count()
    
    return render_template('tickets/index.html', 
                          title='Tickets',
                          tickets=tickets,
                          form=form,
                          all_tickets_count=all_tickets_count,
                          open_tickets_count=open_tickets_count,
                          my_tickets_count=my_tickets_count,
                          unassigned_tickets_count=unassigned_tickets_count,
                          sla_breached_count=sla_breached_count)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
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
        
        if form.assigned_to.data > 0:
            ticket.assigned_to = form.assigned_to.data
            
        if form.due_date.data:
            ticket.due_date = form.due_date.data
            
        if form.assets.data > 0:
            asset = Asset.query.get(form.assets.data)
            if asset:
                ticket.assets.append(asset)
        
        db.session.add(ticket)
        db.session.commit()
        
        flash('Ticket has been created successfully', 'success')
        return redirect(url_for('tickets.view', id=ticket.id))
    
    # Pre-populate with default values
    default_status = TicketStatus.query.filter_by(is_default=True).first()
    if default_status:
        form.status_id.data = default_status.id
        
    default_priority = TicketPriority.query.filter_by(is_default=True).first()
    if default_priority:
        form.priority_id.data = default_priority.id
        
    default_type = TicketType.query.filter_by(is_default=True).first()
    if default_type:
        form.type_id.data = default_type.id
    
    return render_template('tickets/create.html', title='Create Ticket', form=form)

@bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def view(id):
    ticket = Ticket.query.get_or_404(id)
    comment_form = TicketCommentForm()
    time_form = TimeEntryForm()
    
    # Handle comment submission
    if comment_form.submit.data and comment_form.validate():
        comment = TicketComment(
            ticket_id=ticket.id,
            user_id=current_user.id,
            content=comment_form.content.data,
            is_internal=comment_form.is_internal.data
        )
        db.session.add(comment)
        db.session.commit()
        
        flash('Comment added successfully', 'success')
        return redirect(url_for('tickets.view', id=ticket.id))
    
    # Handle time tracking (punch in/out)
    active_time_entry = TimeEntry.query.filter_by(
        ticket_id=ticket.id,
        user_id=current_user.id,
        end_time=None
    ).first()
    
    if time_form.submit_start.data and time_form.validate():
        if active_time_entry:
            flash('You already have an active time entry for this ticket', 'danger')
        else:
            time_entry = TimeEntry(
                ticket_id=ticket.id,
                user_id=current_user.id,
                start_time=datetime.utcnow(),
                notes=time_form.notes.data,
                billable=time_form.billable.data
            )
            db.session.add(time_entry)
            db.session.commit()
            
            flash('Time tracking started', 'success')
        return redirect(url_for('tickets.view', id=ticket.id))
    
    if time_form.submit_stop.data and time_form.validate():
        if not active_time_entry:
            flash('No active time entry found', 'danger')
        else:
            now = datetime.utcnow()
            active_time_entry.end_time = now
            active_time_entry.duration = int((now - active_time_entry.start_time).total_seconds())
            
            if time_form.notes.data:
                if active_time_entry.notes:
                    active_time_entry.notes += f"\n{time_form.notes.data}"
                else:
                    active_time_entry.notes = time_form.notes.data
                    
            db.session.commit()
            
            flash('Time tracking stopped', 'success')
        return redirect(url_for('tickets.view', id=ticket.id))
    
    # Get ticket comments
    comments = TicketComment.query.filter_by(ticket_id=ticket.id).order_by(TicketComment.created_at).all()
    
    # Get time entries
    time_entries = TimeEntry.query.filter_by(ticket_id=ticket.id).order_by(TimeEntry.start_time.desc()).all()
    
    # Calculate total time spent
    total_time = sum([entry.duration or 0 for entry in time_entries if entry.duration])
    
    # Format total time
    hours, remainder = divmod(total_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    formatted_total_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Get related assets
    assets = ticket.assets.all()
    
    # Check SLA status
    sla_response_status = None
    sla_resolution_status = None
    
    if ticket.sla_response_due:
        if ticket.sla_response_met:
            sla_response_status = 'met'
        elif ticket.sla_response_due < datetime.utcnow():
            sla_response_status = 'breached'
        else:
            time_left = ticket.sla_response_due - datetime.utcnow()
            hours_left = time_left.total_seconds() / 3600
            if hours_left < 4:  # Less than 4 hours left
                sla_response_status = 'at_risk'
            else:
                sla_response_status = 'on_track'
    
    if ticket.sla_resolution_due:
        if ticket.sla_resolution_met:
            sla_resolution_status = 'met'
        elif ticket.sla_resolution_due < datetime.utcnow():
            sla_resolution_status = 'breached'
        else:
            time_left = ticket.sla_resolution_due - datetime.utcnow()
            hours_left = time_left.total_seconds() / 3600
            if hours_left < 8:  # Less than 8 hours left
                sla_resolution_status = 'at_risk'
            else:
                sla_resolution_status = 'on_track'
    
    return render_template('tickets/view.html',
                          title=f'Ticket #{ticket.id}',
                          ticket=ticket,
                          comments=comments,
                          comment_form=comment_form,
                          time_form=time_form,
                          time_entries=time_entries,
                          total_time=formatted_total_time,
                          active_time_entry=active_time_entry,
                          assets=assets,
                          sla_response_status=sla_response_status,
                          sla_resolution_status=sla_resolution_status)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    ticket = Ticket.query.get_or_404(id)
    form = TicketForm()
    
    if form.validate_on_submit():
        ticket.subject = form.subject.data
        ticket.description = form.description.data
        ticket.requester_name = form.requester_name.data
        ticket.requester_email = form.requester_email.data
        ticket.status_id = form.status_id.data
        ticket.priority_id = form.priority_id.data
        ticket.type_id = form.type_id.data
        
        if form.assigned_to.data > 0:
            ticket.assigned_to = form.assigned_to.data
        else:
            ticket.assigned_to = None
            
        if form.due_date.data:
            ticket.due_date = form.due_date.data
        else:
            ticket.due_date = None
        
        # Check if status changed to closed
        old_status = TicketStatus.query.get(ticket.status_id)
        new_status = TicketStatus.query.get(form.status_id.data)
        
        if new_status.is_closed and (not old_status.is_closed):
            ticket.resolved_at = datetime.utcnow()
            if ticket.sla_resolution_due and ticket.resolved_at <= ticket.sla_resolution_due:
                ticket.sla_resolution_met = True
        
        db.session.commit()
        
        flash('Ticket has been updated successfully', 'success')
        return redirect(url_for('tickets.view', id=ticket.id))
    
    # Pre-populate form with ticket data
    if request.method == 'GET':
        form.subject.data = ticket.subject
        form.description.data = ticket.description
        form.requester_name.data = ticket.requester_name
        form.requester_email.data = ticket.requester_email
        form.status_id.data = ticket.status_id
        form.priority_id.data = ticket.priority_id
        form.type_id.data = ticket.type_id
        form.assigned_to.data = ticket.assigned_to or 0
        form.due_date.data = ticket.due_date
    
    return render_template('tickets/edit.html', title='Edit Ticket', form=form, ticket=ticket)

@bp.route('/<int:id>/time', methods=['GET', 'POST'])
@login_required
def add_time(id):
    ticket = Ticket.query.get_or_404(id)
    form = ManualTimeEntryForm()
    
    if form.validate_on_submit():
        start_time = form.start_time.data
        end_time = form.end_time.data
        
        if end_time <= start_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('tickets.add_time', id=ticket.id))
        
        duration = int((end_time - start_time).total_seconds())
        
        time_entry = TimeEntry(
            ticket_id=ticket.id,
            user_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            notes=form.notes.data,
            billable=form.billable.data
        )
        
        db.session.add(time_entry)
        db.session.commit()
        
        flash('Time entry added successfully', 'success')
        return redirect(url_for('tickets.view', id=ticket.id))
    
    return render_template('tickets/add_time.html', title='Add Time Entry', form=form, ticket=ticket)

@bp.route('/<int:id>/assign', methods=['POST'])
@login_required
def assign(id):
    ticket = Ticket.query.get_or_404(id)
    user_id = request.form.get('user_id', type=int)
    
    if user_id == 0:
        ticket.assigned_to = None
        message = 'Ticket unassigned successfully'
    else:
        user = User.query.get_or_404(user_id)
        ticket.assigned_to = user.id
        message = f'Ticket assigned to {user.full_name} successfully'
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': message})
    
    flash(message, 'success')
    return redirect(url_for('tickets.view', id=ticket.id))

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    ticket = Ticket.query.get_or_404(id)
    
    # Only administrators can delete tickets
    if not current_user.is_administrator():
        flash('You do not have permission to delete tickets', 'danger')
        return redirect(url_for('tickets.view', id=ticket.id))
    
    db.session.delete(ticket)
    db.session.commit()
    
    flash('Ticket has been deleted successfully', 'success')
    return redirect(url_for('tickets.index'))
