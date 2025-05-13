# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask import render_template, redirect, request, url_for, jsonify
from flask_login import (
    current_user,
    login_user,
    logout_user
)
from flask_dance.contrib.github import github
from flask_dance.contrib.google import google

from apps import db, login_manager, mail
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm, ForgetAccountForm, ResetPasswordForm
from apps.authentication.models import Users, Role, UserInvitationCode, ResetToken
from apps.config import Config
from flask_mail import Message
from apps.authentication.util import verify_pass, hash_pass
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta
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
        
        if not user.is_approved or user.is_deleted:
            return render_template('authentication/login.html',
                                       msg="Nom d'utilisateur ou mot de passe incorrect",
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
        code = request.form['code']

        # Vérifie si le nom d'utilisateur existe déjà
        if Users.query.filter_by(username=username).first():
            return render_template('authentication/register.html',
                                   msg='Username déjà utilisé',
                                   success=False,
                                   form=create_account_form)

        if Users.query.filter_by(email=email).first():
            return render_template('authentication/register.html',
                                   msg='Email déjà utilisé',
                                   success=False,
                                   form=create_account_form)

        # Vérifie si le code d’invitation existe et n’a pas été utilisé
        invitation = UserInvitationCode.query.filter_by(code=code, is_used=False).first()
        if not invitation:
            return render_template('authentication/register.html',
                                   msg='Code d’invitation invalide ou déjà utilisé',
                                   success=False,
                                   form=create_account_form)

        # Créer l’utilisateur avec le rôle associé au code
        user = Users(
            username=username,
            email=email,
            password= request.form['password'],
            role_id=invitation.role_id,
            is_approved=False,
            invite_by  = invitation.utilisateur.username
        )
        # Envoyer l'email ici (à faire avec Flask-Mail)

        destinataire = invitation.utilisateur.email

        msg = Message(
        subject="Invitation à rejoindre la plateforme – Code d'inscription utilisé",
        recipients=[destinataire])

        msg.body = f"""
        Bonjour,

        Le code d'invitation que vous avez généré a été utilisé par l'utilisateur suivant :

        Nom : {username}  
        Email : {email}

        Cet utilisateur a complété son inscription et attend maintenant votre approbation.

        Veuillez vous rendre sur votre tableau de bord pour valider ou refuser sa demande.

        Si vous n'êtes pas à l'origine de cette invitation, vous pouvez simplement ignorer ce message.

        Bien cordialement,  
        L’équipe de gestion
        """

        try:
            mail.send(msg)
            # return jsonify({"message": "📧 Bordereau envoyé avec succès !"})
            flash(f"Invitation envoyée à {email}", "success")
        except Exception as e:
            return jsonify({"message": f"Erreur : {str(e)}"}), 500

        db.session.add(user)
        invitation.is_used = True
        db.session.commit()
        

        # Facultatif : notifier le créateur du code plus tard
        flash("Compte créé. En attente d’approbation par un administrateur.")

        logout_user()
        return render_template('authentication/register.html',
                               msg='Inscription réussie. Veuillez attendre la validation par un administrateur.',
                               success=True,
                               form=create_account_form)

    return render_template('authentication/register.html', form=create_account_form)



@blueprint.route('/forget', methods=['GET', 'POST'])
def forget():
    forget_account_form = ForgetAccountForm(request.form)

    if 'forget' in request.form:
        email = request.form['email']
        user = Users.query.filter_by(email=email).first()

        if user:
            if not user.is_approved or user.is_deleted:
                return render_template('authentication/forget.html',
                                       msg="L'email n'existe pas",
                                       form=forget_account_form)

            # --- 1. Générer un token sécurisé ---
            token = str(uuid.uuid4())
            expire_time = datetime.utcnow() + timedelta(minutes=30)

            # --- 2. Sauvegarder le token et l’expiration dans la base ---
            token = str(uuid.uuid4())
            expire_time = datetime.utcnow() + timedelta(minutes=30)

            reset_entry = ResetToken(
                token=token,
                user_id=user.id,
                expire_at=expire_time
            )
            db.session.add(reset_entry)
            db.session.commit()

            # --- 3. Envoyer le mail ---
            reset_link = url_for('authentication_blueprint.reset_password', token=token, _external=True)
            message = Message(
                subject="Réinitialisation de votre mot de passe",
                recipients=[user.email],
                body=f"Bonjour {user.username},\n\nCliquez sur ce lien pour réinitialiser votre mot de passe :\n{reset_link}\n\nCe lien expire dans 30 minutes.",
                sender="no-reply@tonapp.com"
            )
            mail.send(message)

            return render_template('authentication/forget.html',
                                   msg="Un lien de réinitialisation a été envoyé par email.",
                                   success=True,
                                   form=forget_account_form)
        else:
            return render_template('authentication/forget.html',
                                   msg="L'email n'existe pas",
                                   success=False,
                                   form=forget_account_form)

    return render_template('authentication/forget.html', form=forget_account_form)

@blueprint.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    form = ResetPasswordForm()
    reset_entry = ResetToken.query.filter_by(token=token, used=False).first()

    if not reset_entry or reset_entry.expire_at < datetime.utcnow():
        return render_template('authentication/reset.html', msg="Lien invalide ou expiré", success=True, form=form)
    print("ouiii")

    if request.method == 'POST' :
        if form.validate():
            user = reset_entry.user
            new_password = generate_password_hash(form.password.data)
            user.password = new_password
            reset_entry.used = True
            print("okkkkkkkkkkkkkkkkkkkkk")

            db.session.commit()
            return render_template('authentication/reset.html',
                                    msg="Mot de passe modifié avec succès",
                                    success=True,
                                    form=form)
        else:
            print(form.errors)


    return render_template('authentication/reset.html', form=form)



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
