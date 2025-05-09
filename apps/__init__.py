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
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField,FloatField
from wtforms.validators import DataRequired

# Initialiser Admin
from flask_admin import Admin, AdminIndexView
from flask_login import current_user
from flask_admin.contrib.sqla import ModelView
from apps.models import Journal, PoleActivite, Money, CategorieComptable, CompteComptable

from flask import has_request_context, redirect, url_for

from flask_admin.form import SecureForm
from flask_admin.model.template import EndpointLinkRowAction
from flask_admin.babel import gettext

class CompteComptableForm(FlaskForm):
    numero = StringField('Numéro', validators=[DataRequired()])
    libelle = StringField('Libellé', validators=[DataRequired()])
    is_active = BooleanField('Actif')
class CategorieComptableForm(FlaskForm):
    code = StringField('Code', validators=[DataRequired()])
    libelle = StringField('Libellé', validators=[DataRequired()])
    is_active = BooleanField('Actif')
class MoneyForm(FlaskForm):
    code = StringField('Code', validators=[DataRequired()])
    name = StringField('Nom', validators=[DataRequired()])
    symbol = StringField('Symbole', validators=[DataRequired()])  
    is_active = BooleanField('Actif')           # $
    # is_base_currency = BooleanField('Current')
    rate_to_fcfa = FloatField("en FCFA", validators=[DataRequired()])
class PoleActiviteForm(FlaskForm):
    nom = StringField('Nom', validators=[DataRequired()])
    is_active = BooleanField('Actif') 

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

 

    class CustomAdminView(ModelView):

        def on_form_prefill(self, form, id):
            role_name = getattr(current_user.role, "name", None)
            if role_name not in ['senior', 'superadmin']:
                for field_name in form._fields:
                    if field_name != 'visible':
                        form._fields[field_name].render_kw = {
                            'readonly': True,
                            # 'disabled': True
                        }
        def get_list_row_actions(self):
            role_name = getattr(current_user.role, "name", None)
            #print(role)
            print(role_name)
            if role_name in ['senior', 'superadmin']:
                return super().get_list_row_actions()
            else:
                return [
                    EndpointLinkRowAction(
                        icon_class='fa fa-edit',
                        endpoint='.edit_view',
                        title=gettext('Modifier visibilité')
                    )
                ]


    class MyAdminIndexView(AdminIndexView):
        def is_visible(self):
            return False  # Ne pas afficher dans le menu

        def is_accessible(self):
            return False  # Rend l'accès impossible

        def index(self):
            return redirect(url_for('home_blueprint.index'))  # Redirige ailleurs


    class CompteComptableAdminView(CustomAdminView):
        form = CompteComptableForm
        form_base_class = SecureForm  # important pour CSRF

        
    class CategorieComptableAdminView(CustomAdminView):
        form = CategorieComptableForm
        form_base_class = SecureForm  # important pour CSRF

      
    class MoneyAdminView(CustomAdminView):
        form = MoneyForm
        form_base_class = SecureForm  # important pour CSRF
    class PoleActiviteAdminView(CustomAdminView):
        form = PoleActiviteForm
        form_base_class = SecureForm  # important pour CSRF
    class JournalAdminView(CustomAdminView):
        def is_accessible(self):
            from flask_login import current_user
            role_name = getattr(current_user.role, 'name', None)
            return current_user.is_authenticated and role_name in ['superadmin', 'senior']
        

    admin = Admin(app, name='', template_mode='bootstrap4')
    admin.add_view(JournalAdminView(Journal, db.session))
    admin.add_view(PoleActiviteAdminView(PoleActivite, db.session))
    admin.add_view(MoneyAdminView(Money, db.session))
    admin.add_view(CategorieComptableAdminView(CategorieComptable, db.session))
    admin.add_view(CompteComptableAdminView(CompteComptable, db.session))



    # Initialiser Blueprints
    register_blueprints(app)

    # Authentification OAuth
    app.register_blueprint(github_blueprint, url_prefix="/login")
    app.register_blueprint(google_blueprint, url_prefix="/login")

    return app