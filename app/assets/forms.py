from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, Length
from app.models import User

class AssetForm(FlaskForm):
    name = StringField('Asset Name', validators=[DataRequired(), Length(max=128)])
    asset_type = SelectField('Asset Type', choices=[
        ('computer', 'Computer/Laptop'),
        ('server', 'Server'),
        ('network', 'Network Device'),
        ('peripheral', 'Peripheral'),
        ('mobile', 'Mobile Device'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    serial_number = StringField('Serial Number', validators=[Optional(), Length(max=128)])
    purchase_date = DateField('Purchase Date', format='%Y-%m-%d', validators=[Optional()])
    warranty_expiry = DateField('Warranty Expiry', format='%Y-%m-%d', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('in_use', 'In Use'),
        ('available', 'Available'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired')
    ], validators=[DataRequired()])
    assigned_to_id = SelectField('Assigned To', coerce=int, validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Asset')
    
    def __init__(self, *args, **kwargs):
        super(AssetForm, self).__init__(*args, **kwargs)
        self.assigned_to_id.choices = [(0, 'Unassigned')] + [
            (u.id, u.full_name) for u in User.query.filter(User.is_active == True).all()
        ]

class AssetFilterForm(FlaskForm):
    asset_type = SelectField('Asset Type', choices=[
        ('', 'All Types'),
        ('computer', 'Computer/Laptop'),
        ('server', 'Server'),
        ('network', 'Network Device'),
        ('peripheral', 'Peripheral'),
        ('mobile', 'Mobile Device'),
        ('other', 'Other')
    ], validators=[Optional()])
    status = SelectField('Status', choices=[
        ('', 'All Statuses'),
        ('in_use', 'In Use'),
        ('available', 'Available'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired')
    ], validators=[Optional()])
    assigned_to = SelectField('Assigned To', coerce=int, validators=[Optional()])
    submit = SubmitField('Filter')
    
    def __init__(self, *args, **kwargs):
        super(AssetFilterForm, self).__init__(*args, **kwargs)
        self.assigned_to.choices = [(0, 'All')] + [(u.id, u.full_name) for u in User.query.filter(User.is_active == True).all()]
