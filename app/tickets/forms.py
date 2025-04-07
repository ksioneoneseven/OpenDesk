from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateTimeField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, Optional, Length
from app.models import User, TicketStatus, TicketPriority, TicketType, Asset

class TicketForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[DataRequired()])
    requester_name = StringField('Requester Name', validators=[DataRequired(), Length(max=128)])
    requester_email = StringField('Requester Email', validators=[DataRequired(), Email(), Length(max=128)])
    status_id = SelectField('Status', coerce=int, validators=[DataRequired()])
    priority_id = SelectField('Priority', coerce=int, validators=[DataRequired()])
    type_id = SelectField('Type', coerce=int, validators=[DataRequired()])
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    due_date = DateTimeField('Due Date', format='%Y-%m-%d %H:%M', validators=[Optional()])
    assets = SelectField('Related Assets', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Ticket')
    
    def __init__(self, *args, **kwargs):
        super(TicketForm, self).__init__(*args, **kwargs)
        self.status_id.choices = [(s.id, s.name) for s in TicketStatus.query.all()]
        self.priority_id.choices = [(p.id, p.name) for p in TicketPriority.query.all()]
        self.type_id.choices = [(t.id, t.name) for t in TicketType.query.all()]
        self.assigned_to.choices = [(0, 'Unassigned')] + [
            (u.id, u.full_name) for u in User.query.filter(User.is_active == True).all()
        ]
        self.assets.choices = [(0, 'None')] + [
            (a.id, f"{a.name} ({a.asset_type})") for a in Asset.query.all()
        ]

class TicketCommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired()])
    is_internal = BooleanField('Internal Note')
    submit = SubmitField('Add Comment')

class TimeEntryForm(FlaskForm):
    notes = TextAreaField('Notes', validators=[Optional()])
    billable = BooleanField('Billable', default=True)
    submit_start = SubmitField('Punch In')
    submit_stop = SubmitField('Punch Out')

class ManualTimeEntryForm(FlaskForm):
    start_time = DateTimeField('Start Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    end_time = DateTimeField('End Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    billable = BooleanField('Billable', default=True)
    submit = SubmitField('Add Time Entry')

class TicketFilterForm(FlaskForm):
    status = SelectField('Status', coerce=int, validators=[Optional()])
    priority = SelectField('Priority', coerce=int, validators=[Optional()])
    assigned_to = SelectField('Assigned To', coerce=int, validators=[Optional()])
    date_from = DateTimeField('From Date', format='%Y-%m-%d', validators=[Optional()])
    date_to = DateTimeField('To Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Filter')
    
    def __init__(self, *args, **kwargs):
        super(TicketFilterForm, self).__init__(*args, **kwargs)
        self.status.choices = [(0, 'All')] + [(s.id, s.name) for s in TicketStatus.query.all()]
        self.priority.choices = [(0, 'All')] + [(p.id, p.name) for p in TicketPriority.query.all()]
        self.assigned_to.choices = [(0, 'All')] + [(u.id, u.full_name) for u in User.query.filter(User.is_active == True).all()]
