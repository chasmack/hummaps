from flask.ext.wtf import Form, RecaptchaField
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired


class SearchForm(Form):
    description  = TextAreaField('Description')
    submit = SubmitField('Search')
