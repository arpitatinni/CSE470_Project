from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def init_app(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)
    
    donations = db.relationship('Donation', backref='donor', lazy=True, foreign_keys='Donation.user_id')
    restaurants = db.relationship('Restaurant', backref='user', lazy=True, foreign_keys='Restaurant.user_id')
    ngos = db.relationship('NGO', backref='user', lazy=True, foreign_keys='NGO.user_id')
    volunteers = db.relationship('Volunteer', backref='user', lazy=True, foreign_keys='Volunteer.user_id')

    def set_password(self, password):
        self.password = password

    def check_password(self, password):
        return self.password == password

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role
        }

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    preference = db.Column(db.String(50), nullable=False)  # 'street_animal' or 'people'
    status = db.Column(db.String(50), default='pending')  # pending, accepted, completed, cancelled
    expiry_date = db.Column(db.String(50), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'restaurant_id': self.restaurant_id,
            'food_item': self.description,
            'quantity': self.quantity,
            'recipient_type': self.preference,
            'status': self.status,
            'expiry_date': self.expiry_date.isoformat()
        }

class Restaurant(db.Model):
    __tablename__ = 'restaurant'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    donations = db.relationship('Donation', backref='restaurant', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'address': self.address,
            'cuisine': self.cuisine
        }

class NGO(db.Model):
    __tablename__ = 'ngos'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    focus_area = db.Column(db.String(100), nullable=False)
    service_area = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))
    
    __mapper_args__ = {
        'polymorphic_identity': 'ngo',
        'polymorphic_on': type
    }

class StreetAnimalNGO(NGO):
    __tablename__ = 'street_animal_ngos'
    
    id = db.Column(db.Integer, db.ForeignKey('ngos.id'), primary_key=True)
    animal_type = db.Column(db.String(50), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'street_animal'
    }

class NeedyPeopleNGO(NGO):
    __tablename__ = 'needy_people_ngos'
    
    id = db.Column(db.Integer, db.ForeignKey('ngos.id'), primary_key=True)
    target_demographic = db.Column(db.String(100), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'needy_people'
    }

class Volunteer(db.Model):
    __tablename__ = 'volunteers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    service_area = db.Column(db.String(100), nullable=False)


class DeliveryProof(db.Model):
    __tablename__ = 'delivered'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('donation.id'), nullable=False)
    photo = db.Column(db.String(25600), nullable=False)
    feedback = db.Column(db.String(500))
