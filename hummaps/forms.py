from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired


class SearchForm(Form):
    description  = StringField('Description')
    submit = SubmitField('Search')
