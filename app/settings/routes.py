from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.settings import bp
from app.settings.forms import GeneralSettingsForm, EmailConfigForm, NotificationSettingForm, SLASettingsForm
from app.models import Setting, EmailConfig, NotificationSetting, TicketPriority, User, Role
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_administrator():
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def index():
    return render_template('settings/index.html', title='Settings')

@bp.route('/general', methods=['GET', 'POST'])
@login_required
@admin_required
def general():
    form = GeneralSettingsForm()
    
    if form.validate_on_submit():
        # Update app_name setting
        app_name_setting = Setting.query.filter_by(key='app_name').first()
        if app_name_setting:
            app_name_setting.value = form.app_name.data
        else:
            app_name_setting = Setting(key='app_name', value=form.app_name.data, 
                                      description='Application name displayed in the UI')
            db.session.add(app_name_setting)
        
        # Update company_name setting
        company_name_setting = Setting.query.filter_by(key='company_name').first()
        if company_name_setting:
            company_name_setting.value = form.company_name.data
        else:
            company_name_setting = Setting(key='company_name', value=form.company_name.data, 
                                         description='Company name used in emails and reports')
            db.session.add(company_name_setting)
        
        # Update ticket_id_format setting
        ticket_id_format_setting = Setting.query.filter_by(key='ticket_id_format').first()
        if ticket_id_format_setting:
            ticket_id_format_setting.value = form.ticket_id_format.data
        else:
            ticket_id_format_setting = Setting(key='ticket_id_format', value=form.ticket_id_format.data, 
                                             description='Format for ticket IDs displayed to users')
            db.session.add(ticket_id_format_setting)
        
        db.session.commit()
        flash('General settings updated successfully', 'success')
        return redirect(url_for('settings.general'))
    
    # Pre-populate form with current settings
    if request.method == 'GET':
        app_name_setting = Setting.query.filter_by(key='app_name').first()
        if app_name_setting:
            form.app_name.data = app_name_setting.value
        
        company_name_setting = Setting.query.filter_by(key='company_name').first()
        if company_name_setting:
            form.company_name.data = company_name_setting.value
        
        ticket_id_format_setting = Setting.query.filter_by(key='ticket_id_format').first()
        if ticket_id_format_setting:
            form.ticket_id_format.data = ticket_id_format_setting.value
    
    return render_template('settings/general.html', title='General Settings', form=form)

@bp.route('/email', methods=['GET', 'POST'])
@login_required
@admin_required
def email():
    form = EmailConfigForm()
    
    if form.validate_on_submit():
        # Get existing email config or create new one
        email_config = EmailConfig.query.first()
        if not email_config:
            email_config = EmailConfig()
            db.session.add(email_config)
        
        # Update email config
        email_config.protocol = form.protocol.data
        email_config.server = form.server.data
        email_config.port = form.port.data
        email_config.username = form.username.data
        email_config.password = form.password.data
        email_config.use_ssl = form.use_ssl.data
        email_config.use_tls = form.use_tls.data
        email_config.folder = form.folder.data
        email_config.is_active = form.is_active.data
        
        db.session.commit()
        flash('Email configuration updated successfully', 'success')
        return redirect(url_for('settings.email'))
    
    # Pre-populate form with current settings
    if request.method == 'GET':
        email_config = EmailConfig.query.first()
        if email_config:
            form.protocol.data = email_config.protocol
            form.server.data = email_config.server
            form.port.data = email_config.port
            form.username.data = email_config.username
            form.password.data = email_config.password
            form.use_ssl.data = email_config.use_ssl
            form.use_tls.data = email_config.use_tls
            form.folder.data = email_config.folder
            form.is_active.data = email_config.is_active
    
    return render_template('settings/email.html', title='Email Integration', form=form)

@bp.route('/notifications', methods=['GET', 'POST'])
@login_required
@admin_required
def notifications():
    form = NotificationSettingForm()
    
    if form.validate_on_submit():
        # Update notification settings
        events = {
            'new_ticket': {
                'is_enabled': form.new_ticket.data,
                'recipients': form.new_ticket_recipients.data
            },
            'ticket_assigned': {
                'is_enabled': form.ticket_assigned.data,
                'recipients': form.ticket_assigned_recipients.data
            },
            'ticket_updated': {
                'is_enabled': form.ticket_updated.data,
                'recipients': form.ticket_updated_recipients.data
            },
            'ticket_comment': {
                'is_enabled': form.ticket_comment.data,
                'recipients': form.ticket_comment_recipients.data
            },
            'sla_warning': {
                'is_enabled': form.sla_warning.data,
                'recipients': form.sla_warning_recipients.data
            },
            'sla_breach': {
                'is_enabled': form.sla_breach.data,
                'recipients': form.sla_breach_recipients.data
            },
            'ticket_resolved': {
                'is_enabled': form.ticket_resolved.data,
                'recipients': form.ticket_resolved_recipients.data
            }
        }
        
        for event_type, data in events.items():
            notification = NotificationSetting.query.filter_by(event_type=event_type).first()
            if notification:
                notification.is_enabled = data['is_enabled']
                notification.recipients = data['recipients']
            else:
                notification = NotificationSetting(
                    event_type=event_type,
                    is_enabled=data['is_enabled'],
                    recipients=data['recipients']
                )
                db.session.add(notification)
        
        # Update SLA warning threshold
        sla_threshold_setting = Setting.query.filter_by(key='sla_warning_threshold').first()
        if sla_threshold_setting:
            sla_threshold_setting.value = str(form.sla_warning_threshold.data)
        else:
            sla_threshold_setting = Setting(
                key='sla_warning_threshold',
                value=str(form.sla_warning_threshold.data),
                description='Percentage of SLA time elapsed before warning is triggered'
            )
            db.session.add(sla_threshold_setting)
        
        db.session.commit()
        flash('Notification settings updated successfully', 'success')
        return redirect(url_for('settings.notifications'))
    
    # Pre-populate form with current settings
    if request.method == 'GET':
        notifications = {
            notification.event_type: notification for notification in NotificationSetting.query.all()
        }
        
        if 'new_ticket' in notifications:
            form.new_ticket.data = notifications['new_ticket'].is_enabled
            form.new_ticket_recipients.data = notifications['new_ticket'].recipients
        
        if 'ticket_assigned' in notifications:
            form.ticket_assigned.data = notifications['ticket_assigned'].is_enabled
            form.ticket_assigned_recipients.data = notifications['ticket_assigned'].recipients
        
        if 'ticket_updated' in notifications:
            form.ticket_updated.data = notifications['ticket_updated'].is_enabled
            form.ticket_updated_recipients.data = notifications['ticket_updated'].recipients
        
        if 'ticket_comment' in notifications:
            form.ticket_comment.data = notifications['ticket_comment'].is_enabled
            form.ticket_comment_recipients.data = notifications['ticket_comment'].recipients
        
        if 'sla_warning' in notifications:
            form.sla_warning.data = notifications['sla_warning'].is_enabled
            form.sla_warning_recipients.data = notifications['sla_warning'].recipients
        
        if 'sla_breach' in notifications:
            form.sla_breach.data = notifications['sla_breach'].is_enabled
            form.sla_breach_recipients.data = notifications['sla_breach'].recipients
        
        if 'ticket_resolved' in notifications:
            form.ticket_resolved.data = notifications['ticket_resolved'].is_enabled
            form.ticket_resolved_recipients.data = notifications['ticket_resolved'].recipients
        
        sla_threshold_setting = Setting.query.filter_by(key='sla_warning_threshold').first()
        if sla_threshold_setting:
            form.sla_warning_threshold.data = int(sla_threshold_setting.value)
    
    return render_template('settings/notifications.html', title='Notification Settings', form=form)

@bp.route('/sla', methods=['GET', 'POST'])
@login_required
@admin_required
def sla():
    form = SLASettingsForm()
    
    if form.validate_on_submit():
        # Update SLA settings for each priority
        priorities = {
            'Low': {
                'response_time': form.low_response_time.data,
                'resolution_time': form.low_resolution_time.data
            },
            'Medium': {
                'response_time': form.medium_response_time.data,
                'resolution_time': form.medium_resolution_time.data
            },
            'High': {
                'response_time': form.high_response_time.data,
                'resolution_time': form.high_resolution_time.data
            },
            'Critical': {
                'response_time': form.critical_response_time.data,
                'resolution_time': form.critical_resolution_time.data
            }
        }
        
        for name, times in priorities.items():
            priority = TicketPriority.query.filter_by(name=name).first()
            if priority:
                priority.sla_response_time = times['response_time']
                priority.sla_resolution_time = times['resolution_time']
        
        db.session.commit()
        flash('SLA settings updated successfully', 'success')
        return redirect(url_for('settings.sla'))
    
    # Pre-populate form with current settings
    if request.method == 'GET':
        low_priority = TicketPriority.query.filter_by(name='Low').first()
        if low_priority:
            form.low_response_time.data = low_priority.sla_response_time
            form.low_resolution_time.data = low_priority.sla_resolution_time
        
        medium_priority = TicketPriority.query.filter_by(name='Medium').first()
        if medium_priority:
            form.medium_response_time.data = medium_priority.sla_response_time
            form.medium_resolution_time.data = medium_priority.sla_resolution_time
        
        high_priority = TicketPriority.query.filter_by(name='High').first()
        if high_priority:
            form.high_response_time.data = high_priority.sla_response_time
            form.high_resolution_time.data = high_priority.sla_resolution_time
        
        critical_priority = TicketPriority.query.filter_by(name='Critical').first()
        if critical_priority:
            form.critical_response_time.data = critical_priority.sla_response_time
            form.critical_resolution_time.data = critical_priority.sla_resolution_time
    
    return render_template('settings/sla.html', title='SLA Settings', form=form)
