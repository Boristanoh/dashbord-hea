# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps import db
from sqlalchemy.exc import SQLAlchemyError
from apps.exceptions.exception import InvalidUsage
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property


class Product(db.Model):

    __tablename__ = 'products'

    id            = db.Column(db.Integer,      primary_key=True)
    name          = db.Column(db.String(128),  nullable=False)
    info          = db.Column(db.Text,         nullable=True)
    price         = db.Column(db.Integer,      nullable=False)
    
    def __init__(self, **kwargs):
        super(Product, self).__init__(**kwargs)

    def __repr__(self):
        return f"{self.name} / ${self.price}"

    @classmethod
    def find_by_id(cls, _id: int) -> "Product":
        return cls.query.filter_by(id=_id).first() 

    @classmethod
    def get_list(cls):
        return cls.query.all()

    def save(self) -> None:
        try:
            db.session.add(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise InvalidUsage(error, 422)

    def delete(self) -> None:
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            db.session.close()
            error = str(e.__dict__['orig'])
            raise InvalidUsage(error, 422)
        return
class PoleActivite(db.Model):
    __tablename__ = 'pole_activite'

    id = db.Column(db.Integer, primary_key=True)
    _nom = db.Column('nom', db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    @hybrid_property
    def nom(self):
        return self._nom

    @nom.setter
    def nom(self, value):
        self._nom = value.upper()

    def __repr__(self):
        return f'<PoleActivite {self.nom}>'
    
class CompteComptable(db.Model):
    __tablename__ = 'compte_comptable'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), nullable=False, unique=True)
    libelle = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<CompteComptable {self.numero} - {self.libelle}>'
    
class CategorieComptable(db.Model):
    __tablename__ = 'categorie_comptable'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    libelle = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<CategorieComptable {self.code} - {self.libelle} (Active: {self.is_active})>"
    
class Money(db.Model):
    __tablename__ = 'devise'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False, unique=True)  # USD, EUR, etc.
    name = db.Column(db.String(100), nullable=True)               # Dollar Américain
    symbol = db.Column(db.String(10), nullable=True)              # $
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_base_currency = db.Column(db.Boolean, default=False, nullable=False)  # Ex: XOF = True
    rate_to_fcfa = db.Column(db.Float, nullable=True)
    rate_last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Money {self.code} ({self.name}) - Active: {self.is_active} - Rate to FCFA: {self.rate_to_fcfa}>"
    
class Journal(db.Model):
    __tablename__ = 'operations'

    id = db.Column(db.Integer, primary_key=True)

    date_operation = db.Column(db.Date, nullable=False)

    pole_activite_id = db.Column(db.Integer, db.ForeignKey('pole_activite.id'), nullable=False)
    pole_activite = db.relationship('PoleActivite', backref='operations')

    code_client = db.Column(db.String(100))
    code_fournisseur = db.Column(db.String(100))
    numero_piece = db.Column(db.String(100))

    compte_comptable_id = db.Column(db.Integer, db.ForeignKey('compte_comptable.id'), nullable=False)
    compte_comptable = db.relationship('CompteComptable', backref='operations')

    numero_facture = db.Column(db.String(100))
    designation = db.Column(db.String(255))
    montant = db.Column(db.Numeric(precision=14, scale=2), nullable=False)

    devise_id = db.Column(db.Integer, db.ForeignKey('devise.id'), nullable=False)
    devise = db.relationship('Money', backref='operations')

    montant_fcfa = db.Column(db.Numeric(precision=14, scale=2), nullable=False)

    type_operation = db.Column(db.String(50), nullable=False)
    mode_paiement = db.Column(db.String(50), nullable=False)

    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie_comptable.id'), nullable=False)
    categorie = db.relationship('CategorieComptable', backref='operations')

    enregistre_par = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utilisateur = db.relationship('Users', backref='operations')

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Bordereau(db.Model):
    __tablename__ = 'bordereau'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    nom_entreprise = db.Column(db.String(150), nullable=False)
    adresse_entreprise = db.Column(db.Text, nullable=True)
    numero_facture = db.Column(db.String(100), nullable=False)
    numero_client = db.Column(db.String(100))
    entreprise_contact = db.Column(db.String(120))

    # Client
    client_nom = db.Column(db.String(200))
    client_contact = db.Column(db.String(120))
    client_adresse = db.Column(db.Text, nullable=True)

    # Entête livraison
    po_no = db.Column(db.String(100))
    date_expedition = db.Column(db.Date)
    expedier_via = db.Column(db.String(100))
    vendeur = db.Column(db.String(100))
    fob = db.Column(db.String(100))
    enregistre_par = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utilisateur = db.relationship('Users', backref='bordereaux')
    date_sauvegarde = db.Column(db.DateTime, default=datetime.utcnow)
    envoye_par_mail = db.Column(db.Boolean, default=False)
    date_envoi_mail = db.Column(db.DateTime, nullable=True)


    articles = db.relationship('BordereauArticle', backref='bordereau', lazy=True, cascade="all, delete-orphan")

class BordereauArticle(db.Model):
    __tablename__ = 'bordereau_articles'

    id = db.Column(db.Integer, primary_key=True)
    bordereau_id = db.Column(db.Integer, db.ForeignKey('bordereau.id'), nullable=False)

    numero_article = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float)

    @property
    def total(self):
        return self.quantite * self.prix_unitaire


    