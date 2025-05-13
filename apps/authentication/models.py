# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin

from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin


from apps import db, login_manager
from apps.authentication.util import hash_pass
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Users(db.Model, UserMixin):

    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True)
    email         = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(255), nullable=False)
    bio           = db.Column(db.Text(), nullable=True)
    photo = db.Column(db.String(255), nullable=True, default=None)
    is_deleted = db.Column(db.Boolean, default=False)



    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = db.relationship('Role')
    is_approved = db.Column(db.Boolean, default=False)
    invite_by = db.Column(db.String(64), unique=True)
    invite_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepter_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    oauth_github  = db.Column(db.String(100), nullable=True)
    oauth_google  = db.Column(db.String(100), nullable=True)

    readonly_fields = ["id", "username", "email", "oauth_google"]

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == 'password':
                value = generate_password_hash(value)  # ✔️ retourne une chaîne (str)


            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)

    @classmethod
    def find_by_email(cls, email: str) -> "Users":
        return cls.query.filter_by(email=email).first()

    @classmethod
    def find_by_username(cls, username: str) -> "Users":
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def find_by_id(cls, _id: int) -> "Users":
        return cls.query.filter_by(id=_id).first()
   
    def save(self) -> None:
        try:
            db.session.add(self)
            db.session.commit()
          
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise IntegrityError(error, 422)
    
    def delete_from_db(self) -> None:
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise IntegrityError(error, 422)
        return
    

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __repr__(self):
        return self.name

class UserInvitationCode(db.Model):
    __tablename__ = 'invitation_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    role = db.relationship('Role')
    is_used = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utilisateur = db.relationship('Users', backref='invitation_codes')

@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None

class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="cascade"), nullable=False)
    user = db.relationship(Users)

class ResetToken(db.Model):
    __tablename__ = 'reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(120), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expire_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('Users', backref=db.backref('reset_tokens', lazy=True))
