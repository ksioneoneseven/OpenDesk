from datetime import datetime, timedelta
import pytz
from flask import current_app
from flask_login import UserMixin
from app import db, login_manager, bcrypt
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import event

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    is_active = db.Column(db.Boolean, default=True)
    force_password_change = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    assigned_tickets = db.relationship('Ticket', backref='assigned_agent', lazy='dynamic', 
                                      foreign_keys='Ticket.assigned_to')
    created_tickets = db.relationship('Ticket', backref='creator', lazy='dynamic',
                                     foreign_keys='Ticket.created_by')
    assets = db.relationship('Asset', backref='assigned_user', lazy='dynamic')
    time_entries = db.relationship('TimeEntry', backref='user', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def is_administrator(self):
        return self.role.name == 'Administrator'
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class TicketStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))
    color = db.Column(db.String(7))  # Hex color code
    is_default = db.Column(db.Boolean, default=False)
    is_closed = db.Column(db.Boolean, default=False)
    tickets = db.relationship('Ticket', backref='status', lazy='dynamic')
    
    def __repr__(self):
        return f'<TicketStatus {self.name}>'

class TicketPriority(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))
    color = db.Column(db.String(7))  # Hex color code
    is_default = db.Column(db.Boolean, default=False)
    sla_response_time = db.Column(db.Integer)  # Minutes
    sla_resolution_time = db.Column(db.Integer)  # Minutes
    tickets = db.relationship('Ticket', backref='priority', lazy='dynamic')
    
    def __repr__(self):
        return f'<TicketPriority {self.name}>'

class TicketType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))
    is_default = db.Column(db.Boolean, default=False)
    tickets = db.relationship('Ticket', backref='ticket_type', lazy='dynamic')
    
    def __repr__(self):
        return f'<TicketType {self.name}>'

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    requester_name = db.Column(db.String(128))
    requester_email = db.Column(db.String(128))
    status_id = db.Column(db.Integer, db.ForeignKey('ticket_status.id'))
    priority_id = db.Column(db.Integer, db.ForeignKey('ticket_priority.id'))
    type_id = db.Column(db.Integer, db.ForeignKey('ticket_type.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    
    # SLA tracking
    sla_response_due = db.Column(db.DateTime)
    sla_resolution_due = db.Column(db.DateTime)
    sla_response_met = db.Column(db.Boolean, default=False)
    sla_resolution_met = db.Column(db.Boolean, default=False)
    first_response_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Relationships
    comments = db.relationship('TicketComment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')
    time_entries = db.relationship('TimeEntry', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')
    assets = db.relationship('Asset', secondary='ticket_asset', backref='tickets', lazy='dynamic')
    
    @hybrid_property
    def is_overdue(self):
        if self.due_date and self.due_date < datetime.utcnow():
            return True
        return False
    
    @hybrid_property
    def sla_response_breached(self):
        if self.sla_response_due and not self.sla_response_met and self.sla_response_due < datetime.utcnow():
            return True
        return False
    
    @hybrid_property
    def sla_resolution_breached(self):
        if self.sla_resolution_due and not self.sla_resolution_met and self.sla_resolution_due < datetime.utcnow():
            return True
        return False
    
    @hybrid_property
    def total_time_spent(self):
        return sum([entry.duration for entry in self.time_entries])
    
    def __repr__(self):
        return f'<Ticket {self.id}: {self.subject}>'

class TicketComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_internal = db.Column(db.Boolean, default=False)
    
    # Relationship
    user = db.relationship('User', backref='comments')
    
    def __repr__(self):
        return f'<TicketComment {self.id}>'

class TimeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # Duration in seconds
    notes = db.Column(db.Text)
    billable = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TimeEntry {self.id}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float)
    description = db.Column(db.Text)
    date = db.Column(db.Date)
    billable = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = db.relationship('Ticket', backref='expenses')
    user = db.relationship('User', backref='expenses')
    
    def __repr__(self):
        return f'<Expense {self.id}>'

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    asset_type = db.Column(db.String(64))
    serial_number = db.Column(db.String(128))
    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    notes = db.Column(db.Text)
    status = db.Column(db.String(64))
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Asset {self.id}: {self.name}>'

# Association table for tickets and assets
ticket_asset = db.Table('ticket_asset',
    db.Column('ticket_id', db.Integer, db.ForeignKey('ticket.id'), primary_key=True),
    db.Column('asset_id', db.Integer, db.ForeignKey('asset.id'), primary_key=True)
)

class KnowledgeBaseCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('knowledge_base_category.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    articles = db.relationship('KnowledgeBaseArticle', backref='category', lazy='dynamic')
    subcategories = db.relationship('KnowledgeBaseCategory', backref=db.backref('parent', remote_side=[id]))
    
    def __repr__(self):
        return f'<KBCategory {self.id}: {self.name}>'

class KnowledgeBaseArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('knowledge_base_category.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_kb_articles')
    updater = db.relationship('User', foreign_keys=[updated_by], backref='updated_kb_articles')
    
    def __repr__(self):
        return f'<KBArticle {self.id}: {self.title}>'

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<Setting {self.key}>'

class EmailConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    protocol = db.Column(db.String(10))  # IMAP or Exchange
    server = db.Column(db.String(128))
    port = db.Column(db.Integer)
    username = db.Column(db.String(128))
    password = db.Column(db.String(255))
    use_ssl = db.Column(db.Boolean, default=True)
    use_tls = db.Column(db.Boolean, default=False)
    folder = db.Column(db.String(64), default='INBOX')
    is_active = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<EmailConfig {self.id}: {self.server}>'

class NotificationSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64))  # e.g., 'new_ticket', 'ticket_assigned', 'sla_breach'
    is_enabled = db.Column(db.Boolean, default=True)
    recipients = db.Column(db.Text)  # Comma-separated list of user IDs or 'all_agents', 'admin', etc.
    
    def __repr__(self):
        return f'<NotificationSetting {self.event_type}>'

# Event listeners for SLA calculations
@event.listens_for(Ticket, 'before_insert')
def set_sla_due_dates(mapper, connection, target):
    if target.priority_id:
        priority = TicketPriority.query.get(target.priority_id)
        if priority:
            now = datetime.utcnow()
            if priority.sla_response_time:
                target.sla_response_due = now + timedelta(minutes=priority.sla_response_time)
            if priority.sla_resolution_time:
                target.sla_resolution_due = now + timedelta(minutes=priority.sla_resolution_time)

# Event listener for first response
@event.listens_for(TicketComment, 'after_insert')
def check_first_response(mapper, connection, target):
    ticket = Ticket.query.get(target.ticket_id)
    if ticket and not ticket.first_response_at and target.user_id:
        # Only count agent responses, not requester responses
        user = User.query.get(target.user_id)
        if user and user.role.name in ['Administrator', 'Agent']:
            ticket.first_response_at = datetime.utcnow()
            if ticket.sla_response_due and ticket.first_response_at <= ticket.sla_response_due:
                ticket.sla_response_met = True
            db.session.add(ticket)
            db.session.commit()

# Create default data for the application
def create_default_data():
    # Create default ticket statuses
    statuses = [
        {'name': 'New', 'description': 'Newly created ticket', 'color': '#3498db', 'is_default': True, 'is_closed': False},
        {'name': 'In Progress', 'description': 'Ticket is being worked on', 'color': '#f39c12', 'is_default': False, 'is_closed': False},
        {'name': 'Waiting on Customer', 'description': 'Waiting for customer response', 'color': '#9b59b6', 'is_default': False, 'is_closed': False},
        {'name': 'Resolved', 'description': 'Ticket has been resolved', 'color': '#2ecc71', 'is_default': False, 'is_closed': True},
        {'name': 'Closed', 'description': 'Ticket is closed', 'color': '#7f8c8d', 'is_default': False, 'is_closed': True}
    ]
    
    for status_data in statuses:
        if not TicketStatus.query.filter_by(name=status_data['name']).first():
            status = TicketStatus(**status_data)
            db.session.add(status)
    
    # Create default ticket priorities
    priorities = [
        {'name': 'Low', 'description': 'Low priority issue', 'color': '#3498db', 'is_default': False, 'sla_response_time': 1440, 'sla_resolution_time': 10080},  # 24h response, 7d resolution
        {'name': 'Medium', 'description': 'Medium priority issue', 'color': '#f39c12', 'is_default': True, 'sla_response_time': 480, 'sla_resolution_time': 2880},  # 8h response, 2d resolution
        {'name': 'High', 'description': 'High priority issue', 'color': '#e74c3c', 'is_default': False, 'sla_response_time': 240, 'sla_resolution_time': 1440},  # 4h response, 1d resolution
        {'name': 'Critical', 'description': 'Critical priority issue', 'color': '#c0392b', 'is_default': False, 'sla_response_time': 60, 'sla_resolution_time': 480}  # 1h response, 8h resolution
    ]
    
    for priority_data in priorities:
        if not TicketPriority.query.filter_by(name=priority_data['name']).first():
            priority = TicketPriority(**priority_data)
            db.session.add(priority)
    
    # Create default ticket types
    types = [
        {'name': 'Incident', 'description': 'Something is broken or not working correctly', 'is_default': True},
        {'name': 'Service Request', 'description': 'Request for information or assistance', 'is_default': False},
        {'name': 'Problem', 'description': 'Underlying cause of one or more incidents', 'is_default': False},
        {'name': 'Change Request', 'description': 'Request to add, modify or remove something', 'is_default': False}
    ]
    
    for type_data in types:
        if not TicketType.query.filter_by(name=type_data['name']).first():
            ticket_type = TicketType(**type_data)
            db.session.add(ticket_type)
    
    # Create default notification settings
    notifications = [
        {'event_type': 'new_ticket', 'is_enabled': True, 'recipients': 'all_agents'},
        {'event_type': 'ticket_assigned', 'is_enabled': True, 'recipients': 'assigned_agent'},
        {'event_type': 'ticket_updated', 'is_enabled': True, 'recipients': 'assigned_agent,creator'},
        {'event_type': 'sla_warning', 'is_enabled': True, 'recipients': 'assigned_agent,admin'},
        {'event_type': 'sla_breach', 'is_enabled': True, 'recipients': 'assigned_agent,admin'},
        {'event_type': 'ticket_resolved', 'is_enabled': True, 'recipients': 'creator,requester'}
    ]
    
    for notification_data in notifications:
        if not NotificationSetting.query.filter_by(event_type=notification_data['event_type']).first():
            notification = NotificationSetting(**notification_data)
            db.session.add(notification)
    
    # Create default settings
    settings = [
        {'key': 'app_name', 'value': 'IT Helpdesk', 'description': 'Application name displayed in the UI'},
        {'key': 'company_name', 'value': 'Your Company', 'description': 'Company name used in emails and reports'},
        {'key': 'ticket_id_format', 'value': 'HD-{id:06d}', 'description': 'Format for ticket IDs displayed to users'},
        {'key': 'sla_warning_threshold', 'value': '75', 'description': 'Percentage of SLA time elapsed before warning is triggered'}
    ]
    
    for setting_data in settings:
        if not Setting.query.filter_by(key=setting_data['key']).first():
            setting = Setting(**setting_data)
            db.session.add(setting)
    
    db.session.commit()
