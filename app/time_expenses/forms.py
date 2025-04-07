from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, DateTimeField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from app.models import User, Ticket

class TimeEntryForm(FlaskForm):
    ticket_id = SelectField('Ticket', coerce=int, validators=[DataRequired()])
    start_time = DateTimeField('Start Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    end_time = DateTimeField('End Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    billable = BooleanField('Billable', default=True)
    submit = SubmitField('Save Time Entry')
    
    def __init__(self, *args, **kwargs):
        super(TimeEntryForm, self).__init__(*args, **kwargs)
        self.ticket_id.choices = [(t.id, f"#{t.id} - {t.subject}") for t in Ticket.query.order_by(Ticket.id.desc()).all()]

class ExpenseForm(FlaskForm):
    ticket_id = SelectField('Ticket', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField('Description', validators=[DataRequired()])
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    billable = BooleanField('Billable', default=True)
    submit = SubmitField('Save Expense')
    
    def __init__(self, *args, **kwargs):
        super(ExpenseForm, self).__init__(*args, **kwargs)
        self.ticket_id.choices = [(t.id, f"#{t.id} - {t.subject}") for t in Ticket.query.order_by(Ticket.id.desc()).all()]

class TimeExpenseFilterForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[Optional()])
    ticket_id = SelectField('Ticket', coerce=int, validators=[Optional()])
    date_from = DateField('From Date', format='%Y-%m-%d', validators=[Optional()])
    date_to = DateField('To Date', format='%Y-%m-%d', validators=[Optional()])
    billable_only = BooleanField('Billable Only')
    submit = SubmitField('Filter')
    
    def __init__(self, *args, **kwargs):
        super(TimeExpenseFilterForm, self).__init__(*args, **kwargs)
        self.user_id.choices = [(0, 'All Users')] + [(u.id, u.full_name) for u in User.query.filter(User.is_active == True).all()]
        self.ticket_id.choices = [(0, 'All Tickets')] + [(t.id, f"#{t.id} - {t.subject}") for t in Ticket.query.order_by(Ticket.id.desc()).limit(100).all()]
