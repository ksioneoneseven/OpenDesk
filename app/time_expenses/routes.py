from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.time_expenses import bp
from app.time_expenses.forms import TimeEntryForm, ExpenseForm, TimeExpenseFilterForm
from app.models import TimeEntry, Expense, Ticket, User
from datetime import datetime, timedelta
from sqlalchemy import func, and_

@bp.route('/')
@login_required
def index():
    return redirect(url_for('time_expenses.time_entries'))

@bp.route('/time')
@login_required
def time_entries():
    form = TimeExpenseFilterForm()
    
    # Get filter parameters
    user_id = request.args.get('user_id', type=int, default=0)
    ticket_id = request.args.get('ticket_id', type=int, default=0)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    billable_only = request.args.get('billable_only', type=bool, default=False)
    
    # Base query
    query = TimeEntry.query
    
    # Apply filters
    if user_id > 0:
        query = query.filter(TimeEntry.user_id == user_id)
    
    if ticket_id > 0:
        query = query.filter(TimeEntry.ticket_id == ticket_id)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(TimeEntry.start_time >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)  # Include the entire day
            query = query.filter(TimeEntry.start_time <= to_date)
        except ValueError:
            pass
    
    if billable_only:
        query = query.filter(TimeEntry.billable == True)
    
    # Get time entries
    time_entries = query.order_by(TimeEntry.start_time.desc()).all()
    
    # Calculate total time
    total_seconds = sum([entry.duration or 0 for entry in time_entries])
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    total_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Get summary by user
    user_summary = db.session.query(
        TimeEntry.user_id,
        User.first_name,
        User.last_name,
        func.sum(TimeEntry.duration).label('total_duration')
    ).join(User).group_by(TimeEntry.user_id, User.first_name, User.last_name).all()
    
    user_time_summary = []
    for summary in user_summary:
        hours, remainder = divmod(summary.total_duration or 0, 3600)
        minutes, seconds = divmod(remainder, 60)
        user_time_summary.append({
            'user_id': summary.user_id,
            'name': f"{summary.first_name} {summary.last_name}",
            'total_time': f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        })
    
    # Get summary by ticket
    ticket_summary = db.session.query(
        TimeEntry.ticket_id,
        Ticket.subject,
        func.sum(TimeEntry.duration).label('total_duration')
    ).join(Ticket).group_by(TimeEntry.ticket_id, Ticket.subject).all()
    
    ticket_time_summary = []
    for summary in ticket_summary:
        hours, remainder = divmod(summary.total_duration or 0, 3600)
        minutes, seconds = divmod(remainder, 60)
        ticket_time_summary.append({
            'ticket_id': summary.ticket_id,
            'subject': summary.subject,
            'total_time': f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        })
    
    return render_template('time_expenses/time_entries.html',
                          title='Time Entries',
                          time_entries=time_entries,
                          form=form,
                          total_time=total_time,
                          user_time_summary=user_time_summary,
                          ticket_time_summary=ticket_time_summary)

@bp.route('/time/create', methods=['GET', 'POST'])
@login_required
def create_time_entry():
    form = TimeEntryForm()
    
    if form.validate_on_submit():
        start_time = form.start_time.data
        end_time = form.end_time.data
        
        if end_time <= start_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('time_expenses.create_time_entry'))
        
        duration = int((end_time - start_time).total_seconds())
        
        time_entry = TimeEntry(
            ticket_id=form.ticket_id.data,
            user_id=current_user.id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            notes=form.notes.data,
            billable=form.billable.data
        )
        
        db.session.add(time_entry)
        db.session.commit()
        
        flash('Time entry has been created successfully', 'success')
        return redirect(url_for('time_expenses.time_entries'))
    
    return render_template('time_expenses/create_time_entry.html', title='Create Time Entry', form=form)

@bp.route('/time/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_time_entry(id):
    time_entry = TimeEntry.query.get_or_404(id)
    
    # Only the creator or an administrator can edit time entries
    if time_entry.user_id != current_user.id and not current_user.is_administrator():
        flash('You do not have permission to edit this time entry', 'danger')
        return redirect(url_for('time_expenses.time_entries'))
    
    form = TimeEntryForm()
    
    if form.validate_on_submit():
        start_time = form.start_time.data
        end_time = form.end_time.data
        
        if end_time <= start_time:
            flash('End time must be after start time', 'danger')
            return redirect(url_for('time_expenses.edit_time_entry', id=time_entry.id))
        
        duration = int((end_time - start_time).total_seconds())
        
        time_entry.ticket_id = form.ticket_id.data
        time_entry.start_time = start_time
        time_entry.end_time = end_time
        time_entry.duration = duration
        time_entry.notes = form.notes.data
        time_entry.billable = form.billable.data
        
        db.session.commit()
        
        flash('Time entry has been updated successfully', 'success')
        return redirect(url_for('time_expenses.time_entries'))
    
    if request.method == 'GET':
        form.ticket_id.data = time_entry.ticket_id
        form.start_time.data = time_entry.start_time
        form.end_time.data = time_entry.end_time
        form.notes.data = time_entry.notes
        form.billable.data = time_entry.billable
    
    return render_template('time_expenses/edit_time_entry.html', title='Edit Time Entry', form=form, time_entry=time_entry)

@bp.route('/time/<int:id>/delete', methods=['POST'])
@login_required
def delete_time_entry(id):
    time_entry = TimeEntry.query.get_or_404(id)
    
    # Only the creator or an administrator can delete time entries
    if time_entry.user_id != current_user.id and not current_user.is_administrator():
        flash('You do not have permission to delete this time entry', 'danger')
        return redirect(url_for('time_expenses.time_entries'))
    
    db.session.delete(time_entry)
    db.session.commit()
    
    flash('Time entry has been deleted successfully', 'success')
    return redirect(url_for('time_expenses.time_entries'))

@bp.route('/expenses')
@login_required
def expenses():
    form = TimeExpenseFilterForm()
    
    # Get filter parameters
    user_id = request.args.get('user_id', type=int, default=0)
    ticket_id = request.args.get('ticket_id', type=int, default=0)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    billable_only = request.args.get('billable_only', type=bool, default=False)
    
    # Base query
    query = Expense.query
    
    # Apply filters
    if user_id > 0:
        query = query.filter(Expense.user_id == user_id)
    
    if ticket_id > 0:
        query = query.filter(Expense.ticket_id == ticket_id)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= to_date)
        except ValueError:
            pass
    
    if billable_only:
        query = query.filter(Expense.billable == True)
    
    # Get expenses
    expenses = query.order_by(Expense.date.desc()).all()
    
    # Calculate total amount
    total_amount = sum([expense.amount for expense in expenses])
    
    # Get summary by user
    user_summary = db.session.query(
        Expense.user_id,
        User.first_name,
        User.last_name,
        func.sum(Expense.amount).label('total_amount')
    ).join(User).group_by(Expense.user_id, User.first_name, User.last_name).all()
    
    user_expense_summary = []
    for summary in user_summary:
        user_expense_summary.append({
            'user_id': summary.user_id,
            'name': f"{summary.first_name} {summary.last_name}",
            'total_amount': f"${summary.total_amount:.2f}"
        })
    
    # Get summary by ticket
    ticket_summary = db.session.query(
        Expense.ticket_id,
        Ticket.subject,
        func.sum(Expense.amount).label('total_amount')
    ).join(Ticket).group_by(Expense.ticket_id, Ticket.subject).all()
    
    ticket_expense_summary = []
    for summary in ticket_summary:
        ticket_expense_summary.append({
            'ticket_id': summary.ticket_id,
            'subject': summary.subject,
            'total_amount': f"${summary.total_amount:.2f}"
        })
    
    return render_template('time_expenses/expenses.html',
                          title='Expenses',
                          expenses=expenses,
                          form=form,
                          total_amount=f"${total_amount:.2f}",
                          user_expense_summary=user_expense_summary,
                          ticket_expense_summary=ticket_expense_summary)

@bp.route('/expenses/create', methods=['GET', 'POST'])
@login_required
def create_expense():
    form = ExpenseForm()
    
    if form.validate_on_submit():
        expense = Expense(
            ticket_id=form.ticket_id.data,
            user_id=current_user.id,
            amount=form.amount.data,
            description=form.description.data,
            date=form.date.data,
            billable=form.billable.data
        )
        
        db.session.add(expense)
        db.session.commit()
        
        flash('Expense has been created successfully', 'success')
        return redirect(url_for('time_expenses.expenses'))
    
    return render_template('time_expenses/create_expense.html', title='Create Expense', form=form)

@bp.route('/expenses/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    expense = Expense.query.get_or_404(id)
    
    # Only the creator or an administrator can edit expenses
    if expense.user_id != current_user.id and not current_user.is_administrator():
        flash('You do not have permission to edit this expense', 'danger')
        return redirect(url_for('time_expenses.expenses'))
    
    form = ExpenseForm()
    
    if form.validate_on_submit():
        expense.ticket_id = form.ticket_id.data
        expense.amount = form.amount.data
        expense.description = form.description.data
        expense.date = form.date.data
        expense.billable = form.billable.data
        
        db.session.commit()
        
        flash('Expense has been updated successfully', 'success')
        return redirect(url_for('time_expenses.expenses'))
    
    if request.method == 'GET':
        form.ticket_id.data = expense.ticket_id
        form.amount.data = expense.amount
        form.description.data = expense.description
        form.date.data = expense.date
        form.billable.data = expense.billable
    
    return render_template('time_expenses/edit_expense.html', title='Edit Expense', form=form, expense=expense)

@bp.route('/expenses/<int:id>/delete', methods=['POST'])
@login_required
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    
    # Only the creator or an administrator can delete expenses
    if expense.user_id != current_user.id and not current_user.is_administrator():
        flash('You do not have permission to delete this expense', 'danger')
        return redirect(url_for('time_expenses.expenses'))
    
    db.session.delete(expense)
    db.session.commit()
    
    flash('Expense has been deleted successfully', 'success')
    return redirect(url_for('time_expenses.expenses'))

@bp.route('/report')
@login_required
def report():
    form = TimeExpenseFilterForm()
    
    # Get filter parameters
    user_id = request.args.get('user_id', type=int, default=0)
    ticket_id = request.args.get('ticket_id', type=int, default=0)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    billable_only = request.args.get('billable_only', type=bool, default=False)
    
    # Default to current month if no dates specified
    if not date_from and not date_to:
        today = datetime.today()
        first_day = today.replace(day=1)
        date_from = first_day.strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
    
    # Time entries query
    time_query = TimeEntry.query
    
    # Apply filters to time entries
    if user_id > 0:
        time_query = time_query.filter(TimeEntry.user_id == user_id)
    
    if ticket_id > 0:
        time_query = time_query.filter(TimeEntry.ticket_id == ticket_id)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            time_query = time_query.filter(TimeEntry.start_time >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)  # Include the entire day
            time_query = time_query.filter(TimeEntry.start_time <= to_date)
        except ValueError:
            pass
    
    if billable_only:
        time_query = time_query.filter(TimeEntry.billable == True)
    
    # Expenses query
    expense_query = Expense.query
    
    # Apply filters to expenses
    if user_id > 0:
        expense_query = expense_query.filter(Expense.user_id == user_id)
    
    if ticket_id > 0:
        expense_query = expense_query.filter(Expense.ticket_id == ticket_id)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            expense_query = expense_query.filter(Expense.date >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            expense_query = expense_query.filter(Expense.date <= to_date)
        except ValueError:
            pass
    
    if billable_only:
        expense_query = expense_query.filter(Expense.billable == True)
    
    # Get time entries and expenses
    time_entries = time_query.all()
    expenses = expense_query.all()
    
    # Calculate totals
    total_seconds = sum([entry.duration or 0 for entry in time_entries])
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    total_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    total_expenses = sum([expense.amount for expense in expenses])
    
    # Get summary by ticket
    ticket_summary = []
    tickets = set([entry.ticket_id for entry in time_entries] + [expense.ticket_id for expense in expenses])
    
    for ticket_id in tickets:
        ticket = Ticket.query.get(ticket_id)
        if ticket:
            ticket_time_entries = [entry for entry in time_entries if entry.ticket_id == ticket_id]
            ticket_expenses = [expense for expense in expenses if expense.ticket_id == ticket_id]
            
            total_ticket_seconds = sum([entry.duration or 0 for entry in ticket_time_entries])
            hours, remainder = divmod(total_ticket_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            ticket_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            total_ticket_expenses = sum([expense.amount for expense in ticket_expenses])
            
            ticket_summary.append({
                'ticket_id': ticket_id,
                'subject': ticket.subject,
                'total_time': ticket_time,
                'total_expenses': f"${total_ticket_expenses:.2f}"
            })
    
    return render_template('time_expenses/report.html',
                          title='Time and Expense Report',
                          form=form,
                          time_entries=time_entries,
                          expenses=expenses,
                          total_time=total_time,
                          total_expenses=f"${total_expenses:.2f}",
                          ticket_summary=ticket_summary,
                          date_from=date_from,
                          date_to=date_to)
