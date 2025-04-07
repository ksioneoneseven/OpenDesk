from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, IntegerField, SelectField, PasswordField
from wtforms.validators import DataRequired, Optional, Length, Email, URL, ValidationError

class GeneralSettingsForm(FlaskForm):
    app_name = StringField('Application Name', validators=[DataRequired(), Length(max=64)])
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=64)])
    ticket_id_format = StringField('Ticket ID Format', validators=[DataRequired(), Length(max=32)])
    submit = SubmitField('Save Settings')

class EmailConfigForm(FlaskForm):
    protocol = SelectField('Protocol', choices=[('IMAP', 'IMAP'), ('Exchange', 'Exchange')], validators=[DataRequired()])
    server = StringField('Server Address', validators=[DataRequired(), Length(max=128)])
    port = IntegerField('Port', validators=[DataRequired()])
    username = StringField('Username/Email', validators=[DataRequired(), Length(max=128)])
    password = PasswordField('Password/App Password', validators=[DataRequired()])
    use_ssl = BooleanField('Use SSL', default=True)
    use_tls = BooleanField('Use TLS', default=False)
    folder = StringField('Folder to Monitor', validators=[DataRequired(), Length(max=64)], default='INBOX')
    is_active = BooleanField('Enable Email Integration', default=False)
    submit = SubmitField('Save Email Configuration')

class NotificationSettingForm(FlaskForm):
    new_ticket = BooleanField('New Ticket Created', default=True)
    ticket_assigned = BooleanField('Ticket Assigned', default=True)
    ticket_updated = BooleanField('Ticket Updated', default=True)
    ticket_comment = BooleanField('New Comment Added', default=True)
    sla_warning = BooleanField('SLA Warning', default=True)
    sla_breach = BooleanField('SLA Breach', default=True)
    ticket_resolved = BooleanField('Ticket Resolved', default=True)
    
    new_ticket_recipients = SelectField('New Ticket Recipients', 
                                       choices=[('all_agents', 'All Agents'), 
                                               ('admin', 'Administrators Only')],
                                       validators=[DataRequired()])
    ticket_assigned_recipients = SelectField('Ticket Assigned Recipients', 
                                           choices=[('assigned_agent', 'Assigned Agent Only'), 
                                                   ('all_agents', 'All Agents')],
                                           validators=[DataRequired()])
    ticket_updated_recipients = SelectField('Ticket Updated Recipients', 
                                          choices=[('assigned_agent', 'Assigned Agent Only'), 
                                                  ('assigned_agent_creator', 'Assigned Agent and Creator')],
                                          validators=[DataRequired()])
    ticket_comment_recipients = SelectField('New Comment Recipients', 
                                          choices=[('assigned_agent', 'Assigned Agent Only'), 
                                                  ('assigned_agent_creator', 'Assigned Agent and Creator'),
                                                  ('all_participants', 'All Participants')],
                                          validators=[DataRequired()])
    sla_warning_recipients = SelectField('SLA Warning Recipients', 
                                        choices=[('assigned_agent', 'Assigned Agent Only'), 
                                                ('assigned_agent_admin', 'Assigned Agent and Administrators')],
                                        validators=[DataRequired()])
    sla_breach_recipients = SelectField('SLA Breach Recipients', 
                                       choices=[('assigned_agent', 'Assigned Agent Only'), 
                                               ('assigned_agent_admin', 'Assigned Agent and Administrators'),
                                               ('all_agents', 'All Agents')],
                                       validators=[DataRequired()])
    ticket_resolved_recipients = SelectField('Ticket Resolved Recipients', 
                                           choices=[('creator', 'Creator Only'), 
                                                   ('creator_requester', 'Creator and Requester')],
                                           validators=[DataRequired()])
    
    sla_warning_threshold = IntegerField('SLA Warning Threshold (%)', validators=[DataRequired()], default=75)
    submit = SubmitField('Save Notification Settings')

class SLASettingsForm(FlaskForm):
    low_response_time = IntegerField('Low Priority Response Time (minutes)', validators=[DataRequired()], default=1440)
    low_resolution_time = IntegerField('Low Priority Resolution Time (minutes)', validators=[DataRequired()], default=10080)
    
    medium_response_time = IntegerField('Medium Priority Response Time (minutes)', validators=[DataRequired()], default=480)
    medium_resolution_time = IntegerField('Medium Priority Resolution Time (minutes)', validators=[DataRequired()], default=2880)
    
    high_response_time = IntegerField('High Priority Response Time (minutes)', validators=[DataRequired()], default=240)
    high_resolution_time = IntegerField('High Priority Resolution Time (minutes)', validators=[DataRequired()], default=1440)
    
    critical_response_time = IntegerField('Critical Priority Response Time (minutes)', validators=[DataRequired()], default=60)
    critical_resolution_time = IntegerField('Critical Priority Resolution Time (minutes)', validators=[DataRequired()], default=480)
    
    submit = SubmitField('Save SLA Settings')
