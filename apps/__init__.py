# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_mail import Mail


db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

from apps.authentication.oauth import github_blueprint, google_blueprint


def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)  # ← Ajouté ici


def register_blueprints(app):
    for module_name in ('authentication', 'home', 'dyn_dt', 'charts', ):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

def create_app(config):
    # Contextual
    static_prefix = '/static'
    templates_dir = os.path.dirname(config.BASE_DIR)

    TEMPLATES_FOLDER = os.path.join(templates_dir, 'templates')
    STATIC_FOLDER = os.path.join(templates_dir, 'static')

    print(' > TEMPLATES_FOLDER: ' + TEMPLATES_FOLDER)
    print(' > STATIC_FOLDER:    ' + STATIC_FOLDER)

    app = Flask(__name__, static_url_path=static_prefix, template_folder=TEMPLATES_FOLDER, static_folder=STATIC_FOLDER)
    app.config.from_object(config)

    # Initialiser extensions
    register_extensions(app)

    # Initialiser Admin
    from apps.models import Journal, PoleActivite, Money, CategorieComptable, CompteComptable
    class FullAccessModelView(ModelView):
        can_create = True
        can_edit = True
        can_delete = True

    admin = Admin(app, name='HEA Admin', template_mode='bootstrap4')
    admin.add_view(FullAccessModelView(Journal, db.session))
    admin.add_view(FullAccessModelView(PoleActivite, db.session))
    admin.add_view(FullAccessModelView(Money, db.session))
    admin.add_view(FullAccessModelView(CategorieComptable, db.session))
    admin.add_view(FullAccessModelView(CompteComptable, db.session))


    # Initialiser Blueprints
    register_blueprints(app)

    # Authentification OAuth
    app.register_blueprint(github_blueprint, url_prefix="/login")
    app.register_blueprint(google_blueprint, url_prefix="/login")

    return app
