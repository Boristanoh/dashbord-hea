# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DecimalField, SubmitField, SelectField, DateField, TextAreaField, IntegerField, FloatField,FieldList, FormField
from wtforms.validators import Email, DataRequired, Optional
from flask_wtf.file import FileField
from wtforms_sqlalchemy.fields import QuerySelectField
from apps.models import PoleActivite, CompteComptable, Money, CategorieComptable

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
class ProfileForm(FlaskForm):
        username = StringField('Nom d’utilisateur', validators=[DataRequired()])
        email = StringField('Email', validators=[DataRequired(), Email()])
        bio = TextAreaField('Bio')
        role = StringField('Rôle', render_kw={'readonly': True})  # Lecture seule

class OperationForm(FlaskForm):
    date_operation = DateField('Date de l\'opération', validators=[DataRequired()], format='%Y-%m-%d')

    pole_activite = QuerySelectField(
        'Pôle d\'activité',
        query_factory=lambda: PoleActivite.query.filter_by(is_active=True).all(),
        get_label='nom',
        allow_blank=False,
        validators=[DataRequired()]
    )

    code_client = StringField('Code client')
    code_fournisseur = StringField('Code fournisseur')
    numero_piece = StringField('Numéro de pièce')

    compte_comptable = QuerySelectField(
    'Compte comptable',
    query_factory=lambda: CompteComptable.query.filter_by(is_active=True).all(),
    get_label=lambda c: f"{c.numero} - {c.libelle}",
    allow_blank=False,
    validators=[DataRequired()]
)


    numero_facture = StringField('Numéro de facture')
    designation = StringField('Désignation')
    montant = DecimalField('Montant', places=2, validators=[DataRequired()])

    devise = QuerySelectField(
        'Devise',
        query_factory=lambda: Money.query.filter_by(is_active=True).all(),
        get_label='code',
        allow_blank=False,
        validators=[DataRequired()]
    )

    type_operation = SelectField(
        'Type d\'opération',
        choices=[
            ('debit', "Entrée d'argent( Debit)"),
            ('credit', "Sortie d' argent ( Credit)"),
        ],
        validators=[DataRequired()]
    )

    mode_paiement = SelectField(
        'Mode de paiement',
        choices=[
            ('carte', 'Carte bancaire'),
            ('espece', 'Espèce'),
            ('cheque', 'Chèque'),
            
        ],
        validators=[DataRequired()]
    )

    categorie = QuerySelectField(
        'Catégorie',
        query_factory=lambda: CategorieComptable.query.filter_by(is_active=True).all(),
        get_label=lambda c: f"{c.code} - {c.libelle}",
        allow_blank=False,
        validators=[DataRequired()]
        
    )

    submit = SubmitField('Enregistrer l\'opération')



class ArticleForm(FlaskForm):
    class Meta:
        csrf = False  # <- désactive la vérification CSRF pour les champs dynamiques
    numero_article = StringField("Numéro d'article", validators=[DataRequired()])
    descriptions = StringField("Description", validators=[DataRequired()])  # ✅ doit être un champ WTForms ici
    quantite = IntegerField("Quantité", validators=[DataRequired()])
    prix_unitaire = FloatField("Prix Unitaire", validators=[DataRequired()])

class BordereauForm(FlaskForm):
    # Infos entreprise (expéditeur)
    date = DateField("Date", validators=[DataRequired()])
    nom_entreprise = StringField("Nom de l'Entreprise", validators=[DataRequired()])
    adresse_entreprise = TextAreaField("Adresse de l'Entreprise", validators=[Optional()])
    numero_facture = StringField("N° Facture", validators=[DataRequired()])
    numero_client = StringField("N° Client", validators=[Optional()])
    entreprise_contact = StringField("Point de Contact (Entreprise)", validators=[Optional()])

    # Infos client
    client_nom = StringField("Nom du Client", validators=[Optional()])
    client_contact = StringField("Point de Contact (Client)", validators=[Optional()])
    client_adresse = TextAreaField("Adresse du Client", validators=[Optional()])

    # Entête livraison
    po_no = StringField("P.O. No.", validators=[Optional()])
    date_expedition = DateField("Date d'expédition", validators=[Optional()])
    expedier_via = StringField("Expédier via", validators=[Optional()])
    vendeur = StringField("Vendeur", validators=[Optional()])
    fob = StringField("FOB", validators=[Optional()])

    # Articles
    articles = FieldList(FormField(ArticleForm), min_entries=1)

    # Bouton
    submit = SubmitField("Enregistrer le Bordereau")
