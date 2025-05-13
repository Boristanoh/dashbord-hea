# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import Email, DataRequired,  EqualTo, Length

# login and registration

class LoginForm(FlaskForm):
    username = StringField('Username',
                         id='username_login',
                         validators=[DataRequired()])
    password = PasswordField('Password',
                             id='pwd_login',
                             validators=[DataRequired()])

class CreateAccountForm(FlaskForm):
    username = StringField('Username',
                         id='username_create',
                         validators=[DataRequired()])
    email = StringField('Email',
                      id='email_create',
                      validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             id='pwd_create',
                             validators=[DataRequired()])
    code = StringField('Code d’invitation', validators=[DataRequired()])

class ForgetAccountForm(FlaskForm):
    email = StringField('Email',
                      id='email_user',
                      validators=[DataRequired(), Email()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        'Nouveau mot de passe',
        validators=[
            DataRequired(message="Veuillez entrer un mot de passe."),
            Length(min=6, message="Le mot de passe doit contenir au moins 6 caractères.")
        ]
    )

    confirm_password = PasswordField(
        'Confirmer le mot de passe',
        validators=[
            DataRequired(message="Veuillez confirmer votre mot de passe."),
            EqualTo('password', message="Les mots de passe ne correspondent pas.")
        ]
    )

