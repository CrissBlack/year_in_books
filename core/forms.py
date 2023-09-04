from flask_wtf import FlaskForm
from flask import flash
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, EmailField, IntegerField, validators, ValidationError
from wtforms.validators import InputRequired, Length, Email, Optional, EqualTo, NumberRange
from .models import User, Bookshelf


class SearchBooks(FlaskForm):
    query = StringField('Title', validators=[InputRequired()])
    submit = SubmitField(label='Search')


class Login(FlaskForm):
    username = StringField('Username', validators=[InputRequired('Username required')])
    password = PasswordField('Password', validators=[InputRequired('Password required')])
    submit = SubmitField(label='Login')

    def validate_username(form, field):
        found_user = User.query.filter_by(username=field.data).first()
        if not found_user:
            flash('Username not found.')
            raise validators.ValidationError()

class Register(FlaskForm):
    username = StringField('Username',
                           validators=[InputRequired('Username required'),
                                       Length(min=5, message='Username should be at least 5 characters long')])

    password = PasswordField('Password',
                             validators=[InputRequired('Password required'),
                                         Length(min=6, max=25, message='Password should be between 6 and 25 characters long')])

    confirm_password = PasswordField('Confirm Password',
                                     validators=[InputRequired('Confirm password'),
                                                 EqualTo('password', message="Passwords don't match")])

    email = EmailField('Email', validators=[Optional(strip_whitespace=True), Email('invalid email')])
    submit = SubmitField(label='Register')

class ChallengeForm(FlaskForm):
    challenge = IntegerField('Challenge', validators=[InputRequired('You must enter a number'),
                                                     NumberRange(min=1, max=999, message='Enter a number between 1 and 999')])
    cancel_challenge = SubmitField('Cancel challenge')
    update_challenge = SubmitField('Save')

class NewShelf(FlaskForm):
    shelf_input = StringField('Shelf name', validators=[InputRequired('Must enter a shelf name.'),
                                                        Length(min=2, message='At least two characters required.')])
    submit = SubmitField('Add')

    @staticmethod
    def validate_shelf_input(form, field):
        found_shelf = Bookshelf.query.filter(
            Bookshelf.user_id == current_user.id).filter(
            Bookshelf.name == field.data
        ).first()
        if found_shelf:
            raise ValidationError('Shelf already exists.')