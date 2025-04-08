from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateTimeField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo, ValidationError
from app.models import TicketStatus, TicketPriority, TicketType, User

class TicketForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[DataRequired()])
    requester_name = StringField('Requester Name', validators=[DataRequired(), Length(max=128)])
    requester_email = StringField('Requester Email', validators=[DataRequired(), Email(), Length(max=128)])
    status_id = SelectField('Status', coerce=int)
    priority_id = SelectField('Priority', coerce=int)
    type_id = SelectField('Type', coerce=int)
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    due_date = DateTimeField('Due Date', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(TicketForm, self).__init__(*args, **kwargs)
        self.status_id.choices = [(s.id, s.name) for s in TicketStatus.query.all()]
        self.priority_id.choices = [(p.id, p.name) for p in TicketPriority.query.all()]
        self.type_id.choices = [(t.id, t.name) for t in TicketType.query.all()]
        
        # Add empty choice for assigned_to
        self.assigned_to.choices = [(0, 'Unassigned')] + [
            (u.id, u.username) for u in User.query.filter_by(is_active=True).all()
        ]

class TicketCommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    is_internal = SelectField('Comment Type', choices=[(False, 'Public'), (True, 'Internal')], coerce=bool)
    submit = SubmitField('Add Comment')

class TicketAssignForm(FlaskForm):
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    submit = SubmitField('Assign Ticket')
    
    def __init__(self, *args, **kwargs):
        super(TicketAssignForm, self).__init__(*args, **kwargs)
        # Add empty choice for assigned_to
        self.assigned_to.choices = [(0, 'Unassigned')] + [
            (u.id, u.username) for u in User.query.filter_by(is_active=True).all()
        ]

class TicketStatusForm(FlaskForm):
    status_id = SelectField('Status', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Update Status')
    
    def __init__(self, *args, **kwargs):
        super(TicketStatusForm, self).__init__(*args, **kwargs)
        self.status_id.choices = [(s.id, s.name) for s in TicketStatus.query.all()]

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    role = SelectField('Role', choices=[('Administrator', 'Administrator'), ('Agent', 'Agent'), ('User', 'User')])
    is_active = BooleanField('Active')
    submit = SubmitField('Save')
    
    def __init__(self, *args, **kwargs):
        self.original_username = kwargs.pop('original_username', None)
        self.original_email = kwargs.pop('original_email', None)
        super(UserForm, self).__init__(*args, **kwargs)
    
    def validate_username(self, username):
        if self.original_username and self.original_username == username.data:
            return
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        if self.original_email and self.original_email == email.data:
            return
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please choose a different one.')

class SettingsForm(FlaskForm):
    theme = SelectField('Theme', choices=[('light', 'Light Mode'), ('dark', 'Dark Mode')])
    submit = SubmitField('Save Settings')
