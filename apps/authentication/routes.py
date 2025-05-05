# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask import render_template, redirect, request, url_for
from flask_login import (
    current_user,
    login_user,
    logout_user
)
from flask_dance.contrib.github import github
from flask_dance.contrib.google import google

from apps import db, login_manager
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import Users, Role
from apps.config import Config

from apps.authentication.util import verify_pass, hash_pass
from werkzeug.security import generate_password_hash, check_password_hash

# Login & Registration

# @blueprint.route("/github")
# def login_github():
#     """ Github login """
#     if not github.authorized:
#         return redirect(url_for("github.login"))

#     res = github.get("/user")
#     return redirect(url_for('home_blueprint.index'))
import os
from werkzeug.utils import secure_filename
from flask import current_app, request, redirect, url_for, flash
from flask_login import current_user, login_required

@blueprint.route('/upload-photo', methods=['POST'])
@login_required
def upload_photo():
    file = request.files.get('photo')
    if file and file.filename:
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.static_folder, 'uploads/profils')
        os.makedirs(upload_path, exist_ok=True)
        filepath = os.path.join(upload_path, filename)
        file.save(filepath)

        # Met à jour l'utilisateur
        current_user.photo = filename
        db.session.commit()
        flash("Photo mise à jour avec succès", "success")
    else:
        flash("Aucune image sélectionnée", "danger")
    return redirect(url_for('home_blueprint.profile'))

@blueprint.route('/delete-photo', methods=['POST'])
@login_required
def delete_photo():
    if current_user.photo:
        upload_path = os.path.join(current_app.static_folder, 'uploads/profils')
        photo_path = os.path.join(upload_path, current_user.photo)
        
        if os.path.exists(photo_path):
            os.remove(photo_path)
        
        # Réinitialise le champ photo
        current_user.photo = None
        db.session.commit()
        flash("Photo supprimée. L'image par défaut est maintenant utilisée.", "success")
    else:
        flash("Aucune photo à supprimer.", "warning")
    
    return redirect(url_for('home_blueprint.profile'))

@blueprint.route('/create_superadmin')
def create_superadmin():

    role = Role.query.filter_by(name='admin').first()
    if not role:
        return "❌ Rôle 'superadmin' non trouvé."

    if Users.query.filter_by(username='admin').first():
        return "⚠️ Utilisateur déjà existant."

    user = Users(
        username='test',
        email='test@example.com',
        password='pass',
        role_id=role.id,
        is_approved=True
    )

    db.session.add(user)
    db.session.commit()

    return "✅ Superadmin créé avec succès !"

@blueprint.route("/google")
def login_google():
    """ Google login """
    if not google.authorized:
        return redirect(url_for("google.login"))

    res = google.get("/oauth2/v1/userinfo")
    return redirect(url_for('home_blueprint.index'))

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)

    if 'login' in request.form:

        # lire les données du formulaire
        user_id = request.form['username']  # peut être username ou email
        password = request.form['password']

        # Trouver l'utilisateur
        user = Users.find_by_username(user_id)

        if not user:
            user = Users.find_by_email(user_id)
            if not user:
                return render_template('authentication/login.html',
                                       msg='Utilisateur ou email inconnu',
                                       form=login_form)

        # Vérifier le mot de passe haché
        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home_blueprint.index'))

        # Erreur : mauvais identifiants
        return render_template('authentication/login.html',
                               msg="Nom d'utilisateur ou mot de passe incorrect",
                               form=login_form)

    # Si utilisateur non connecté, afficher le formulaire
    if not current_user.is_authenticated:
        return render_template('authentication/login.html',
                               form=login_form)

    # Sinon, redirection vers l'accueil
    return redirect(url_for('home_blueprint.index'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)

    if 'register' in request.form:

        username = request.form['username']
        email = request.form['email']

        # Vérifie si le nom d'utilisateur existe déjà
        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('authentication/register.html',
                                   msg='Username already registered',
                                   success=False,
                                   form=create_account_form)

        # Vérifie si l'email existe déjà
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('authentication/register.html',
                                   msg='Email already registered',
                                   success=False,
                                   form=create_account_form)

        # Créer l'utilisateur (le mot de passe est hashé automatiquement dans Users.__init__)
        user = Users(
            username=username,
            email=email,
            password=request.form['password']  # ⚠️ mot de passe brut ici
        )
        db.session.add(user)
        db.session.commit()

        logout_user()

        return render_template('authentication/register.html',
                               msg='User created successfully.',
                               success=True,
                               form=create_account_form)

    return render_template('authentication/register.html', form=create_account_form)

@blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home_blueprint.index'))

# Errors

@blueprint.context_processor
def has_github():
    return {'has_github': bool(Config.GITHUB_ID) and bool(Config.GITHUB_SECRET)}

@blueprint.context_processor
def has_google():
    return {'has_google': bool(Config.GOOGLE_ID) and bool(Config.GOOGLE_SECRET)}

@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect('/login')
