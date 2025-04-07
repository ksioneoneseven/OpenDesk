from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, Length
from app.models import KnowledgeBaseCategory

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=128)])
    description = TextAreaField('Description', validators=[Optional()])
    parent_id = SelectField('Parent Category', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Category')
    
    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.parent_id.choices = [(0, 'None (Top Level)')] + [
            (c.id, c.name) for c in KnowledgeBaseCategory.query.order_by(KnowledgeBaseCategory.name).all()
        ]

class ArticleForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=255)])
    content = TextAreaField('Content', validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    is_published = BooleanField('Published', default=True)
    submit = SubmitField('Save Article')
    
    def __init__(self, *args, **kwargs):
        super(ArticleForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in KnowledgeBaseCategory.query.order_by(KnowledgeBaseCategory.name).all()]

class KnowledgeBaseSearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    submit = SubmitField('Search')
    
    def __init__(self, *args, **kwargs):
        super(KnowledgeBaseSearchForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(0, 'All Categories')] + [
            (c.id, c.name) for c in KnowledgeBaseCategory.query.order_by(KnowledgeBaseCategory.name).all()
        ]
