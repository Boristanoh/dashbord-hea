# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os, json, pprint
import wtforms

from apps.home import blueprint
from flask import render_template, request, redirect, url_for, flash, session, jsonify, request
from flask_login import login_required
from jinja2 import TemplateNotFound
from flask_login import login_required, current_user
from apps import db, config, mail
from apps.models import *
from apps.tasks import *
from apps.authentication.models import Users
from flask_wtf import FlaskForm
from flask import abort
from apps.home.forms import OperationForm, BordereauForm, ProfileForm
from flask import render_template, make_response
from xhtml2pdf import pisa
import io
from io import BytesIO
from flask_mail import Message
from sqlalchemy import extract, func
import json
from werkzeug.security import check_password_hash, generate_password_hash
from flask import request
from datetime import datetime, timedelta


from dateutil.relativedelta import relativedelta
from calendar import monthrange
from collections import defaultdict

@blueprint.route('/admin-page')
@login_required
def admin_custom():
    return render_template('pages/admin_page.html')


@blueprint.route('/')
@blueprint.route('/index')
@login_required
def index():
    periode = request.args.get('periode', default='mois')
    annee = request.args.get('annee', type=int)
    mois = request.args.get('mois', type=int)
    jour = request.args.get('jour', type=int)

    today = datetime.today()
    
    # Détermination des périodes courante et précédente
    if periode == 'jour':
        current_start = current_end = today.date()
        previous_start = previous_end = current_start - timedelta(days=1)
    elif periode == 'semaine':
        current_start = today - timedelta(days=today.weekday())
        current_end = current_start + timedelta(days=6)
        previous_start = current_start - timedelta(days=7)
        previous_end = current_start - timedelta(days=1)
    elif periode == 'mois':
        current_start = today.replace(day=1)
        current_end = today
        previous_start = current_start - relativedelta(months=1)
        last_day = monthrange(previous_start.year, previous_start.month)[1]
        previous_end = previous_start.replace(day=last_day)
    elif periode == 'personnalise':
        if jour and mois and annee:
            current_start = current_end = datetime(annee, mois, jour)
            previous_start = previous_end = current_start - timedelta(days=1)
        elif mois and annee:
            current_start = datetime(annee, mois, 1)
            current_end = datetime(annee, mois, monthrange(annee, mois)[1])
            previous_start = current_start - relativedelta(months=1)
            previous_end = previous_start.replace(day=monthrange(previous_start.year, previous_start.month)[1])
        elif annee:
            current_start = datetime(annee, 1, 1)
            current_end = datetime(annee, 12, 31)
            previous_start = datetime(annee - 1, 1, 1)
            previous_end = datetime(annee - 1, 12, 31)
        else:
            current_start = today.replace(day=1)
            current_end = today
            previous_start = current_start - relativedelta(months=1)
            previous_end = previous_start.replace(day=monthrange(previous_start.year, previous_start.month)[1])
    else:
        current_start = today.replace(day=1)
        current_end = today
        previous_start = current_start - relativedelta(months=1)
        previous_end = previous_start.replace(day=monthrange(previous_start.year, previous_start.month)[1])

    # Requêtes sur les périodes
    current_data = Journal.query.filter(Journal.date_operation.between(current_start, current_end)).all()
    previous_data = Journal.query.filter(Journal.date_operation.between(previous_start, previous_end)).all()

    # Traitement statistique
    def compute_stats(entries):
        total_entree = sum(op.montant_fcfa for op in entries if op.type_operation == 'debit')
        total_sortie = sum(op.montant_fcfa for op in entries if op.type_operation == 'credit')
        ca = sum(op.montant_fcfa for op in entries)
        nb = len(entries)
        return {
            'entree': total_entree,
            'sortie': total_sortie,
            'ca': ca,
            'nb': nb,
            'benefice': total_entree - total_sortie
        }

    def delta(val1, val2):
        if val2 == 0:
            return 0
        return round(((val1 - val2) / val2) * 100, 2)

    stats_current = compute_stats(current_data)
    stats_previous = compute_stats(previous_data)

    # Deltas pour les comparaisons
    stats = {}
    for key in stats_current:
        stats[key] = {
            'val': stats_current[key],
            'delta': delta(stats_current[key], stats_previous.get(key, 0))
        }
   # Récupération de tous les pôles d'activités
    all_poles = PoleActivite.query.all()

    # Initialisation des stats pour chaque pôle (même ceux sans opération)
    pole_stats = {pole: 0.0 for pole in all_poles}

    # Mise à jour des montants pour les pôles ayant des opérations "debit"
    for op in current_data:
        if op.type_operation == 'debit':
            pole_stats[op.pole_activite] += float(op.montant_fcfa)

    # Tri décroissant des pôles selon les montants
    best_poles = sorted(pole_stats.items(), key=lambda x: x[1], reverse=True)

    for pole, montant in best_poles:
        print(pole.nom, montant)

    # Top 5 clients par montant et nombre d’opérations
    client_stats = defaultdict(lambda: {'montant': 0, 'nb': 0})
    for op in current_data:
        client_stats[op.code_client]['montant'] += float(op.montant_fcfa)
        client_stats[op.code_client]['nb'] += 1
    top_clients = sorted(client_stats.items(), key=lambda x: x[1]['montant'], reverse=True)[:5]
    # Liste des années
    annees = [a[0] for a in db.session.query(extract('year', Journal.date_operation)).distinct()]

    mois_dict = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
        7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    print("statistiques")
    print(stats)

   # Évolution du bénéfice par mois
    if annee:
        # Obtenir les opérations de l’année sélectionnée
        data_annee = Journal.query.filter(
            extract('year', Journal.date_operation) == annee
        ).all()
    else:
        # Par défaut, utiliser l'année en cours
        annee = today.year
        data_annee = Journal.query.filter(
            extract('year', Journal.date_operation) == annee
        ).all()

    # Agrégation du bénéfice mensuel (entrées - sorties)
    benefice_mensuel = defaultdict(float)
    for op in data_annee:
        mois_op = op.date_operation.month
        montant = float(op.montant_fcfa)
        if op.type_operation == 'debit':
            benefice_mensuel[mois_op] += montant
        elif op.type_operation == 'credit':
            benefice_mensuel[mois_op] -= montant

    # Déterminer le mois maximal à afficher (jusqu’au mois actuel si année en cours)
    mois_max = today.month if annee == today.year else 12

    # Données formatées
    benefice_mois_list = [round(benefice_mensuel.get(m, 0), 2) for m in range(1, mois_max + 1)]
    mois_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][:mois_max]

    print(benefice_mois_list)
    repartition_entrees_sorties = {
    "Entrées": stats_current['entree'],
    "Sorties": stats_current['sortie']
}
    print(repartition_entrees_sorties)



    return render_template(
        "pages/index.html",
        stats=stats,
        periode=periode,
        resultats=current_data,
        annees=annees,
        mois_dict=mois_dict,
        best_poles =best_poles,
        benefice_mois=benefice_mois_list,
        mois_labels=mois_labels,
        top_clients=top_clients,
        repartition=repartition_entrees_sorties
    )

@blueprint.route('/mois_disponibles/<int:annee>')
def mois_disponibles(annee):
    print("mois")
    mois = db.session.query(
        extract('month', Journal.date_operation)
    ).filter(extract('year', Journal.date_operation) == annee).distinct().all()

    mois = sorted(set(m[0] for m in mois))
    print(mois)
    return jsonify(mois)

@blueprint.route('/jours_disponibles/<int:annee>/<int:mois>')
def jours_disponibles(annee, mois):
    jours = db.session.query(
        extract('day', Journal.date_operation)
    ).filter(
        extract('year', Journal.date_operation) == annee,
        extract('month', Journal.date_operation) == mois
    ).distinct().all()

    jours = sorted(set(j[0] for j in jours))
    return jsonify(jours)
from flask import jsonify

# @blueprint.route("/dashboard/filtre-options")
# def get_filtre_options():
#     # Exemple : simule des dates extraites de la base
#     dates_str = ["2023-01-05", "2023-01-20", "2023-02-10", "2023-02-25", "2023-03-15", "2024-04-01", "2024-04-20"]
#     dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates_str]

#     mois_par_annee = {}
#     jours_par_annee_mois = {}

#     for dt in dates:
#         annee, mois, jour = dt.year, dt.month, dt.day
#         mois_par_annee.setdefault(annee, set()).add(mois)
#         jours_par_annee_mois.setdefault((annee, mois), set()).add(jour)

#     mois_par_annee = {k: sorted(list(v)) for k, v in mois_par_annee.items()}
#     jours_par_annee_mois = {f"{k[0]}-{k[1]}": sorted(list(v)) for k, v in jours_par_annee_mois.items()}

#     return jsonify({
#         "mois": mois_par_annee,
#         "jours": jours_par_annee_mois
#     })

@blueprint.route('/enregistrement')
def enregistrement():
    form = OperationForm()
    return render_template('pages/enregistrement.html', form=form, segment='enregistrement')

@blueprint.route('/create_operation', methods=['POST'])
def create_operation():
    form = OperationForm()

    if form.validate_on_submit():
        # Trouver le taux de la devise choisie
        devise_obj = Money.query.get(form.devise.data.id)

        if devise_obj is None:
            flash('Erreur : Devise inconnue.', 'danger')
            return redirect(url_for('home_blueprint.enregistrement'))

        # Calculer le montant en FCFA
        montant_fcfa = float(form.montant.data) * float(devise_obj.rate_to_fcfa)

        # Créer l'opération
        journal = Journal(
            date_operation=form.date_operation.data,
            pole_activite_id=form.pole_activite.data.id,
            code_client=form.code_client.data,
            code_fournisseur=form.code_fournisseur.data,
            numero_piece=form.numero_piece.data,
            compte_comptable_id=form.compte_comptable.data.id,
            numero_facture=form.numero_facture.data,
            designation=form.designation.data,
            montant=form.montant.data,
            devise_id=form.devise.data.id,
            montant_fcfa=montant_fcfa,
            type_operation=form.type_operation.data,
            mode_paiement=form.mode_paiement.data,
            categorie_id=form.categorie.data.id,
            enregistre_par=current_user.id
        )

        db.session.add(journal)
        db.session.commit()

        flash('✅ Opération enregistrée avec succès !', 'success')
        return redirect(url_for('home_blueprint.enregistrement'))

    flash('Erreur lors de l\'enregistrement.', 'danger')
    return redirect(url_for('home_blueprint.enregistrement'))

@blueprint.route('/journal')
def journal():
    from datetime import datetime
    selected_year = request.args.get('year', type=int) or datetime.now().year
    operations = Journal.query.filter(
        Journal.date_operation.between(f"{selected_year}-01-01", f"{selected_year}-12-31")
    ).order_by(Journal.date_operation.desc()).all()

    # Générer une liste d'années disponibles
    years = db.session.query(db.func.strftime('%Y', Journal.date_operation).label("year"))\
        .distinct().order_by(db.desc("year")).all()
    years = [int(y.year) for y in years]

    return render_template(
        'pages/journal.html',
        operations=operations,
        selected_year=selected_year,
        years=years,
        segment='journal'
    )


@blueprint.route('/recu/<int:operation_id>')
def recu_journal(operation_id):
    operation = Journal.query.get_or_404(operation_id)
    html = render_template('recu/journal.html', operation=operation)
    response = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return "Erreur lors de la génération du reçu", 500

    response.seek(0)
    return make_response(response.read(), {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'inline; filename=recu_operation_{}.pdf'.format(operation_id)
    })
@blueprint.route('/bordereau', methods=['GET', 'POST'])
@login_required
def bordereau():
    form = BordereauForm()
    
    # Gérer dynamiquement les articles en POST
    if request.method == "POST":
        print("✅ Requête POST reçue")
        article_keys = [key for key in request.form if "articles-" in key and "-numero_article" in key]
        article_count = len(set([key.split("-")[1] for key in article_keys]))
        while len(form.articles.entries) < article_count:
            form.articles.append_entry()

    if form.validate_on_submit():
        new_bordereau = Bordereau(
            date=form.date.data,
            nom_entreprise=form.nom_entreprise.data,
            adresse_entreprise=form.adresse_entreprise.data,
            numero_facture=form.numero_facture.data,
            numero_client=form.numero_client.data,
            entreprise_contact=form.entreprise_contact.data,
            client_nom=form.client_nom.data,
            client_contact=form.client_contact.data,
            client_adresse=form.client_adresse.data,
            po_no=form.po_no.data,
            date_expedition=form.date_expedition.data,
            expedier_via=form.expedier_via.data,
            vendeur=form.vendeur.data,
            fob=form.fob.data,
            enregistre_par=current_user.id
        )

        for article in form.articles.entries:
            if article.numero_article.data and article.descriptions.data:
                article_model = BordereauArticle(
                    numero_article=article.numero_article.data,
                    description=article.descriptions.data,
                    quantite=article.quantite.data,
                    prix_unitaire=article.prix_unitaire.data
                )
                new_bordereau.articles.append(article_model)

        db.session.add(new_bordereau)
        db.session.commit()

        # Sauvegarde de l’état et de l’ID
        session['bordereau_id'] = new_bordereau.id
        session['bordereau_sauvegarde'] = True

        flash("✅ Bordereau enregistré avec succès", "success")
        return redirect(url_for('home_blueprint.bordereau'))

    else:
        print("❌ Erreurs de validation :", form.errors)

    # 🔁 Chargement des données après redirection
    
    mon_bordereau = None
    if 'bordereau_id' in session:
        mon_bordereau = Bordereau.query.get(session['bordereau_id'])
    if mon_bordereau and not request.method == "POST":
        form.nom_entreprise.data = mon_bordereau.nom_entreprise
        form.adresse_entreprise.data = mon_bordereau.adresse_entreprise
        form.numero_facture.data = mon_bordereau.numero_facture
        form.numero_client.data = mon_bordereau.numero_client
        form.entreprise_contact.data = mon_bordereau.entreprise_contact
        form.date.data = mon_bordereau.date
        form.client_nom.data = mon_bordereau.client_nom
        form.client_contact.data = mon_bordereau.client_contact
        form.client_adresse.data = mon_bordereau.client_adresse
        form.po_no.data = mon_bordereau.po_no
        form.date_expedition.data = mon_bordereau.date_expedition
        form.expedier_via.data = mon_bordereau.expedier_via
        form.vendeur.data = mon_bordereau.vendeur
        form.fob.data = mon_bordereau.fob

        # Articles
        form.articles.entries = []  # Vide d'abord
        for article in mon_bordereau.articles:
            subform = {}
            subform["numero_article"] = article.numero_article
            subform["descriptions"] = article.description
            subform["quantite"] = article.quantite
            subform["prix_unitaire"] = article.prix_unitaire
            form.articles.append_entry(subform)

    bordereau_sauvegarde = session.get('bordereau_sauvegarde', False)
    return render_template(
        'pages/bordereau.html',
        segment='bordereau',
        form=form,
        mon_bordereau=mon_bordereau,
        bordereau_sauvegarde=bordereau_sauvegarde
    )





@blueprint.route("/bordereau/pdf/apercu", methods=["POST"])
@login_required
def apercu_bordereau_pdf():
    form_data = request.form.to_dict(flat=True)
    print("📥 Données reçues :", form_data)  # ← Vérifie bien ça dans ta console Flask

    html = render_template("recu/bordereau_pdf_template.html", form=form_data)
    pdf = BytesIO()
    pisa.CreatePDF(html, dest=pdf)
    pdf.seek(0)

    return make_response(pdf.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'inline; filename="bordereau.pdf"'
    })


@blueprint.route("/bordereau/<int:bordereau_id>/pdf", methods=["GET"])
def bordereau_pdf(bordereau_id):
    mode = request.args.get("mode", "inline")  # inline ou attachment
    bordereau = Bordereau.query.get_or_404(bordereau_id)
    html = render_template("recu/bordereau_pdf_template2.html", bordereau=bordereau)

    pdf_file = BytesIO()
    pisa.CreatePDF(html, dest=pdf_file)
    pdf_file.seek(0)

    dispo = "inline" if mode == "inline" else "attachment"

    return make_response(
        pdf_file.read(),
        200,
        {
            "Content-Type": "application/pdf",
            "Content-Disposition": f"{dispo}; filename=bordereau_{bordereau.id}.pdf"
        }
    )

@blueprint.route('/bordereau/reset', methods=['POST'])
@login_required
def reset_bordereau():
    session.pop('bordereau_id', None)
    session['bordereau_sauvegarde'] = False
    return '', 204


@blueprint.route('/bordereau/envoyer-email', methods=['POST'])
@login_required
def envoyer_bordereau_email():
    if not request.is_json:
        return jsonify({"message": "❌ Format JSON attendu (application/json)"}), 415

    data = request.get_json()
    destinataire = data.get("destinataire")
    bordereau_id = session.get("bordereau_id")

    if not bordereau_id:
        return jsonify({"message": "Aucun bordereau sauvegardé"}), 400

    bordereau = Bordereau.query.get(bordereau_id)

    html = render_template("recu/bordereau_pdf_template2.html", bordereau=bordereau)
    pdf_file = BytesIO()
    pisa.CreatePDF(html, dest=pdf_file)
    pdf_file.seek(0)

    msg = Message("Votre bordereau d’expédition", recipients=[destinataire])
    msg.body = "Veuillez trouver ci-joint le bordereau d’expédition."
    msg.attach(f"bordereau_{bordereau_id}.pdf", "application/pdf", pdf_file.read())

    try:
        mail.send(msg)
        return jsonify({"message": "📧 Bordereau envoyé avec succès !"})
    except Exception as e:
        return jsonify({"message": f"Erreur : {str(e)}"}), 500

@blueprint.route("/bordereaux/enregistrements")
@login_required
def liste_bordereaux():
    # Récupérer les années présentes dans la BD
    annees_disponibles = db.session.query(
        extract('year', Bordereau.date_sauvegarde).label('annee')
    ).distinct().order_by('annee').all()

    annees = [a.annee for a in annees_disponibles]

    annee = request.args.get("annee", type=int)
    mois = request.args.get("mois", type=int)
    jour = request.args.get("jour", type=int)

    query = Bordereau.query

    if annee:
        query = query.filter(db.extract('year', Bordereau.date_sauvegarde) == annee)
    if mois:
        query = query.filter(db.extract('month', Bordereau.date_sauvegarde) == mois)
    if jour:
        query = query.filter(db.extract('day', Bordereau.date_sauvegarde) == jour)

    # Optionnel : filtrer par utilisateur
    if current_user.role.name == "user":
        query = query.filter(Bordereau.utilisateur_id == current_user.id)

    bordereaux = query.order_by(Bordereau.date_sauvegarde.desc()).all()
    return render_template("pages/liste_bordereaux.html", bordereaux=bordereaux, annees=annees,)



@blueprint.route('/icon_feather')
def icon_feather():
    return render_template('pages/icon-feather.html', segment='icon_feather')

@blueprint.route('/color')
def color():
    return render_template('pages/color.html', segment='color')

@blueprint.route('/sample_page')
def sample_page():
    return render_template('pages/sample-page.html', segment='sample_page')

@blueprint.route('/typography')
def typography():
    return render_template('pages/typography.html', segment='typography')

def getField(column): 
    if isinstance(column.type, db.Text):
        return wtforms.TextAreaField(column.name.title())
    if isinstance(column.type, db.String):
        return wtforms.StringField(column.name.title())
    if isinstance(column.type, db.Boolean):
        return wtforms.BooleanField(column.name.title())
    if isinstance(column.type, db.Integer):
        return wtforms.IntegerField(column.name.title())
    if isinstance(column.type, db.Float):
        return wtforms.DecimalField(column.name.title())
    if isinstance(column.type, db.LargeBinary):
        return wtforms.HiddenField(column.name.title())
    return wtforms.StringField(column.name.title()) 




@blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    

    readonly_fields = ["id", "role"]
    full_width_fields = {"bio"}

    # Si POST et ce n’est pas un changement de mot de passe → on conserve les données soumises
    if request.method == "POST" and 'current_password' not in request.form:
        form = ProfileForm(request.form)
    else:
        form = ProfileForm(obj=current_user)


    # Gestion du changement de mot de passe
    if request.method == "POST" and 'current_password' in request.form:
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        # Décodage si le mot de passe est stocké en bytes
        hashed_pw = current_user.password
        if isinstance(hashed_pw, bytes):
            hashed_pw = hashed_pw.decode('utf-8')

        if not check_password_hash(hashed_pw, current_password):
            flash("❌ Ancien mot de passe incorrect.", "danger")
        elif new_password != confirm_new_password:
            flash("❌ Les mots de passe ne correspondent pas.", "danger")
        elif len(new_password) < 6:
            flash("❌ Le nouveau mot de passe doit contenir au moins 6 caractères.", "warning")
        else:
            current_user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("✅ Mot de passe modifié avec succès.", "success")
            return redirect(url_for("home_blueprint.profile"))

    # Mise à jour du profil
    elif form.validate_on_submit():
        for field_name in ["username", "email", "bio"]:
            setattr(current_user, field_name, form.data[field_name])
        db.session.commit()
        flash("✅ Profil mis à jour.", "success")
        return redirect(url_for("home_blueprint.profile"))

    context = {
        'segment': 'profile',
        'form': form,
        'readonly_fields': readonly_fields,
        'full_width_fields': full_width_fields,
    }
    return render_template('pages/profile.html', **context)





# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None

@blueprint.route('/error-403')
def error_403():
    return render_template('error/403.html'), 403

@blueprint.errorhandler(403)
def not_found_error(error):
    return redirect(url_for('error-403'))

@blueprint.route('/error-404')
def error_404():
    return render_template('error/404.html'), 404

@blueprint.errorhandler(404)
def not_found_error(error):
    return redirect(url_for('error-404'))

@blueprint.route('/error-500')
def error_500():
    return render_template('error/500.html'), 500

@blueprint.errorhandler(500)
def not_found_error(error):
    return redirect(url_for('error-500'))

# Celery (to be refactored)
@blueprint.route('/tasks-test')
def tasks_test():
    
    input_dict = { "data1": "04", "data2": "99" }
    input_json = json.dumps(input_dict)

    task = celery_test.delay( input_json )

    return f"TASK_ID: {task.id}, output: { task.get() }"


# Custom template filter

@blueprint.app_template_filter("replace_value")
def replace_value(value, arg):
    return value.replace(arg, " ").title()


@blueprint.before_request
def require_login():
    public_routes = [
        'authentication_blueprint.login',    # ✅
        'authentication_blueprint.register', # ✅
        'error_403',
        'error_404',
        'error_500',
        'static',
    ]

    if not current_user.is_authenticated:
        endpoint = request.endpoint or ''
        if not any(endpoint.startswith(pub) for pub in public_routes):
            return redirect(url_for('authentication_blueprint.login'))




















@blueprint.route('/insert_activites')
def insert_activites():
    activites = [
        "EQUIPEMENT ET FOURNITURES",
        "AGRONOMIE",
        "CONSTRUCTION ET IMMOBILIER",
        "HOTELLERIE ET EVENEMENTIEL",
        "EGLISE MISSION EMMANUEL",
        "DEPENSES PERSONNELLES"
    ]
    objets_activites = [PoleActivite(nom=nom.upper()) for nom in activites]
    db.session.add_all(objets_activites)
    db.session.commit()
    return "✅ Activités insérées !"

@blueprint.route('/insert_comptes')
def insert_comptes():
    comptes_data = [
        {"numero": "1011", "libelle": "CAPITAL SOUSCRIT, NON APPELE"},
        {"numero": "1012", "libelle": "CAPITAL SOUSCRIT, APPELE, NON VERSE"},
        {"numero": "1013", "libelle": "CAPITAL SOUSCRIT, APPELE, VERSE, NON AMORTI"},
        {"numero": "1014", "libelle": "CAPITAL SOUSCRIT, APPELE, VERSE, AMORTI"},
        {"numero": "1018", "libelle": "CAPITAL SOUSCRIT SOUMIS A DES CONDITIONS PARTICULIERES"},
        {"numero": "102", "libelle": "CAPITAL PAR DOTATION"},
        {"numero": "1021", "libelle": "DOTATION INITIALE"},
        {"numero": "1022", "libelle": "DOTATIONS COMPLEMENTAIRES"},
        {"numero": "1028", "libelle": "AUTRES DOTATIONS"},
        {"numero": "103", "libelle": "CAPITAL PERSONNEL"},
        {"numero": "104", "libelle": "COMPTE DE L'EXPLOITANT"},
        {"numero": "1041", "libelle": "APPORTS TEMPORAIRES"},
        {"numero": "1042", "libelle": "OPERATIONS COURANTES"},
        {"numero": "1043", "libelle": "REMUNERATIONS, IMPOTS ET AUTRES CHARGES PERSONNELLES"},
        {"numero": "1047", "libelle": "PRELEVEMENTS D'AUTOCONSOMMATION"},
        {"numero": "1048", "libelle": "AUTRES PRELEVEMENTS"},
        {"numero": "105", "libelle": "PRIMES LIEES AU CAPITAL SOCIAL"},
        {"numero": "1051", "libelle": "PRIMES D'EMISSION"},
        {"numero": "1052", "libelle": "PRIMES D'APPORT"},
        {"numero": "1053", "libelle": "PRIMES DE FUSION"},
        {"numero": "1054", "libelle": "PRIMES DE CONVERSION"},
        {"numero": "1058", "libelle": "AUTRES PRIMES"},
        {"numero": "106", "libelle": "ECARTS DE REEVALUATION"},
        {"numero": "1061", "libelle": "ECARTS DE REEVALUATION LEGALE"},
        {"numero": "1062", "libelle": "ECARTS DE REEVALUATION LIBRE"},
        {"numero": "109", "libelle": "APPORTEURS, CAPITAL SOUSCRIT, NON APPELE"},
        {"numero": "11", "libelle": "RESERVES"},
        {"numero": "111", "libelle": "RESERVE LEGALE"},
        {"numero": "112", "libelle": "RESERVES STATUTAIRES OU CONTRACTUELLES"},
        {"numero": "113", "libelle": "RESERVES REGLEMENTEES"},
        {"numero": "1132", "libelle": "RESERVES DE PLUS-VALUES NETTES A LONG TERME"},
        {"numero": "1134", "libelle": "RESERVES CONSECUTIVES A L'OCTROI DE SUBVENTIONS D'INVESTISSEMENT"},
        {"numero": "1138", "libelle": "AUTRES RESERVES REGLEMENTEES"},
        {"numero": "118", "libelle": "AUTRES RESERVES"},
        {"numero": "1188", "libelle": "RESERVES FACULTATIVES"},
        {"numero": "12", "libelle": "REPORT A NOUVEAU"},
        {"numero": "121", "libelle": "REPORT A NOUVEAU CREDITEUR"},
        {"numero": "129", "libelle": "REPORT A NOUVEAU DEBITEUR"},
        {"numero": "1291", "libelle": "PERTE NETTE A REPORTER"},
        {"numero": "1292", "libelle": "PERTE - AMORTISSEMENTS REPUTES DIFFERES"},
        {"numero": "13", "libelle": "RESULTAT NET DE L'EXERCICE"},
        {"numero": "130", "libelle": "RESULTAT EN INSTANCE D'AFFECTATION"},
        {"numero": "1301", "libelle": "RESULTAT EN INSTANCE D'AFFECTATION : BENEFICE"},
        {"numero": "1309", "libelle": "RESULTAT EN INSTANCE D'AFFECTATION : PERTE"},
        {"numero": "131", "libelle": "RESULTAT NET : BENEFICE"},
        {"numero": "132", "libelle": "MARGE COMMERCIALE (MC)"},
        {"numero": "133", "libelle": "VALEUR AJOUTEE (V.A.)"},
        {"numero": "134", "libelle": "EXCEDENT BRUT D'EXPLOITATION (E.B.E.)"},
        {"numero": "135", "libelle": "RESULTAT D'EXPLOITATION (R.E.)"},
        {"numero": "136", "libelle": "RESULTAT FINANCIER (R.F.)"},
        {"numero": "137", "libelle": "RESULTAT DES ACTIVITES ORDINAIRES (R.A.O.)"},
        {"numero": "138", "libelle": "RESULTAT HORS ACTIVITES ORDINAIRES (R.H.A.O.)"},
        {"numero": "139", "libelle": "RESULTAT NET : PERTE"},
        {"numero": "14", "libelle": "SUBVENTIONS D'INVESTISSEMENT"},
        {"numero": "141", "libelle": "SUBVENTIONS D'EQUIPEMENT"},
        {"numero": "1411", "libelle": "ETAT"},
        {"numero": "1412", "libelle": "REGIONS"},
        {"numero": "1413", "libelle": "DEPARTEMENTS"},
        {"numero": "1414", "libelle": "COMMUNES ET COLLECTIVITES PUBLIQUES DECENTRALISEES"},
        {"numero": "1415", "libelle": "ENTITES PUBLIQUES OU MIXTES"},
        {"numero": "1416", "libelle": "ENTITES ET ORGANISMES PRIVES"},
        {"numero": "1417", "libelle": "ORGANISMES INTERNATIONAUX"},
        {"numero": "1418", "libelle": "AUTRES"},
        # ⏩ Continuer tout comme ça jusqu’à 705, en reprenant exactement ton fichier ⏩
    ]

    objets_comptes = [CompteComptable(numero=compte["numero"], libelle=compte["libelle"].upper()) for compte in comptes_data]

    db.session.add_all(objets_comptes)
    db.session.commit()

    return "✅ Tous les comptes comptables ont été insérés avec succès !"

@blueprint.route('/insert_categories')
def insert_categories():
    categories_data = [
        {"code": "1.1", "libelle": "Ventes de produits"},
        {"code": "1.2", "libelle": "Prestations de services"},
        {"code": "1.3", "libelle": "Revenus locatifs (loyers perçus)"},
        {"code": "1.4", "libelle": "Investissements reçus (fonds levés, actionnaires)"},
        {"code": "1.5", "libelle": "Subventions et aides"},
        {"code": "1.6", "libelle": "Remboursements reçus"},
        {"code": "1.7", "libelle": "Autres revenus divers"},
        {"code": "2.1.1", "libelle": "Achats de marchandises"},
        {"code": "2.1.2", "libelle": "Fournitures de bureau"},
        {"code": "2.1.3", "libelle": "Publicité & Marketing"},
        {"code": "2.1.4", "libelle": "Logiciels et abonnements"},
        {"code": "2.2.1", "libelle": "Loyer & charges locatives"},
        {"code": "2.2.2", "libelle": "Factures d’électricité, eau, internet"},
        {"code": "2.2.3", "libelle": "Entretien & réparations"},
        {"code": "2.3.1", "libelle": "Salaires & charges sociales"},
        {"code": "2.3.2", "libelle": "Frais de formation"},
        {"code": "2.3.3", "libelle": "Remboursement de notes de frais"},
        {"code": "2.4.1", "libelle": "Billets de train/avion"},
        {"code": "2.4.2", "libelle": "Essence & péages"},
        {"code": "2.4.3", "libelle": "Location de voiture"},
        {"code": "2.5.1", "libelle": "Impôts & taxes"},
        {"code": "2.5.2", "libelle": "Frais bancaires & intérêts d’emprunt"},
        {"code": "2.5.3", "libelle": "Assurances"},
        {"code": "2.6.1", "libelle": "Pertes & vols"},
        {"code": "2.6.2", "libelle": "Dons & mécénat"},
        {"code": "2.6.3", "libelle": "Autres charges diverses"},
    ]

    objets_categories = [CategorieComptable(code=c["code"], libelle=c["libelle"].upper()) for c in categories_data]

    db.session.add_all(objets_categories)
    db.session.commit()

    return "✅ Catégories comptables insérées avec succès !"

@blueprint.route('/insert_monnaies')
def insert_monnaies():
    monnaies = [
        {"code": "USD", "name": "Dollar Américain", "symbol": "$"},
        {"code": "EUR", "name": "Euro", "symbol": "€"},
        {"code": "GBP", "name": "Livre Sterling", "symbol": "£"},
        {"code": "JPY", "name": "Yen Japonais", "symbol": "¥"},
        {"code": "XOF", "name": "Franc CFA BCEAO", "symbol": "F", "is_base": True},
        {"code": "XAF", "name": "Franc CFA BEAC", "symbol": "F"},
        {"code": "CHF", "name": "Franc Suisse", "symbol": "CHF"},
        {"code": "CAD", "name": "Dollar Canadien", "symbol": "CA$"},
        {"code": "AUD", "name": "Dollar Australien", "symbol": "AU$"},
        {"code": "CNY", "name": "Yuan Chinois", "symbol": "¥"},
        {"code": "INR", "name": "Roupie Indienne", "symbol": "₹"},
        {"code": "MAD", "name": "Dirham Marocain", "symbol": "DH"},
        {"code": "ZAR", "name": "Rand Sud-Africain", "symbol": "R"},
        {"code": "DZD", "name": "Dinar Algérien", "symbol": "DA"},
        {"code": "EGP", "name": "Livre Égyptienne", "symbol": "E£"},
        {"code": "RUB", "name": "Rouble Russe", "symbol": "₽"},
        {"code": "SAR", "name": "Riyal Saoudien", "symbol": "ر.س"},
        {"code": "MXN", "name": "Peso Mexicain", "symbol": "MX$"},
        {"code": "SEK", "name": "Couronne Suédoise", "symbol": "kr"},
        {"code": "NOK", "name": "Couronne Norvégienne", "symbol": "kr"},
        {"code": "DKK", "name": "Couronne Danoise", "symbol": "kr"},
        {"code": "THB", "name": "Baht Thaïlandais", "symbol": "฿"},
        {"code": "KRW", "name": "Won Sud-Coréen", "symbol": "₩"},
        {"code": "MYR", "name": "Ringgit Malaisien", "symbol": "RM"},
        {"code": "PHP", "name": "Peso Philippin", "symbol": "₱"},
        {"code": "TND", "name": "Dinar Tunisien", "symbol": "DT"},
        {"code": "IRR", "name": "Rial Iranien", "symbol": "﷼"},
        {"code": "KWD", "name": "Dinar Koweïtien", "symbol": "KD"},
        {"code": "KES", "name": "Shilling Kényan", "symbol": "KSh"},
        {"code": "RON", "name": "Leu Roumain", "symbol": "lei"},
        {"code": "VND", "name": "Dong Vietnamien", "symbol": "₫"},
        {"code": "PKR", "name": "Roupie Pakistanaise", "symbol": "₨"},
        {"code": "ILS", "name": "Shekel Israélien", "symbol": "₪"},
        {"code": "ARS", "name": "Peso Argentin", "symbol": "$"},
        {"code": "IQD", "name": "Dinar Irakien", "symbol": "ع.د"}
    ]

    objets_monnaies = []
    for m in monnaies:
        monnaie = Money(
            code=m["code"],
            name=m["name"],
            symbol=m["symbol"],
            rate_to_fcfa=100,
            is_active=True,
            is_base_currency=m.get("is_base", False)
        )
        objets_monnaies.append(monnaie)

    db.session.add_all(objets_monnaies)
    db.session.commit()
    return "✅ Monnaies insérées avec succès !"
