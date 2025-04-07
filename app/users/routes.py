from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db, bcrypt
from app.users import bp
from app.users.forms import UserForm, EditUserForm
from app.models import User, Role, Ticket, TimeEntry
from app.settings.routes import admin_required
from sqlalchemy import func

@bp.route('/')
@login_required
@admin_required
def index():
    users = User.query.all()
    return render_template('users/index.html', title='User Administration', users=users)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    form = UserForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role_id=form.role_id.data,
            is_active=form.is_active.data,
            force_password_change=form.force_password_change.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {user.username} has been created successfully', 'success')
        return redirect(url_for('users.index'))
    
    return render_template('users/create.html', title='Create User', form=form)

@bp.route('/<int:id>', methods=['GET'])
@login_required
@admin_required
def view(id):
    user = User.query.get_or_404(id)
    
    # Get user statistics
    assigned_tickets_count = Ticket.query.filter_by(assigned_to=user.id).count()
    open_tickets_count = Ticket.query.filter_by(assigned_to=user.id).join(Ticket.status).filter_by(is_closed=False).count()
    
    # Get time tracking statistics
    total_time = db.session.query(func.sum(TimeEntry.duration)).filter(TimeEntry.user_id == user.id).scalar() or 0
    hours, remainder = divmod(total_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    formatted_total_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Get recent activity
    recent_tickets = Ticket.query.filter_by(assigned_to=user.id).order_by(Ticket.updated_at.desc()).limit(5).all()
    recent_time_entries = TimeEntry.query.filter_by(user_id=user.id).order_by(TimeEntry.created_at.desc()).limit(5).all()
    
    return render_template('users/view.html', 
                          title=f'User: {user.full_name}',
                          user=user,
                          assigned_tickets_count=assigned_tickets_count,
                          open_tickets_count=open_tickets_count,
                          total_time=formatted_total_time,
                          recent_tickets=recent_tickets,
                          recent_time_entries=recent_time_entries)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    user = User.query.get_or_404(id)
    form = EditUserForm(user.username, user.email)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role_id = form.role_id.data
        user.is_active = form.is_active.data
        user.force_password_change = form.force_password_change.data
        
        if form.password.data:
            user.set_password(form.password.data)
        
        db.session.commit()
        
        flash(f'User {user.username} has been updated successfully', 'success')
        return redirect(url_for('users.view', id=user.id))
    
    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.role_id.data = user.role_id
        form.is_active.data = user.is_active
        form.force_password_change.data = user.force_password_change
    
    return render_template('users/edit.html', title='Edit User', form=form, user=user)

@bp.route('/<int:id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate(id):
    user = User.query.get_or_404(id)
    
    # Prevent deactivating yourself
    if user.id == current_user.id:
        flash('You cannot deactivate your own account', 'danger')
        return redirect(url_for('users.view', id=user.id))
    
    user.is_active = False
    db.session.commit()
    
    flash(f'User {user.username} has been deactivated', 'success')
    return redirect(url_for('users.index'))

@bp.route('/<int:id>/activate', methods=['POST'])
@login_required
@admin_required
def activate(id):
    user = User.query.get_or_404(id)
    
    user.is_active = True
    db.session.commit()
    
    flash(f'User {user.username} has been activated', 'success')
    return redirect(url_for('users.index'))

@bp.route('/<int:id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(id):
    user = User.query.get_or_404(id)
    
    # Generate a random password
    import random
    import string
    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    user.set_password(temp_password)
    user.force_password_change = True
    db.session.commit()
    
    flash(f'Password for {user.username} has been reset to: {temp_password}', 'success')
    flash('The user will be required to change their password on next login', 'info')
    
    return redirect(url_for('users.view', id=user.id))
