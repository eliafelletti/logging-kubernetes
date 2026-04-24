from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

'''
    This module defines the database models for the application. It uses SQLAlchemy to create a User model with fields for id, username, email, and created_at. 
    The User model also includes a method to convert the object to a dictionary for easy JSON serialization and a string representation for debugging purposes.
'''

# DB initialization
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users' # Table name in the database

    # Columns
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.timezone.utc.now)

    # Method to convert the User object to a JSON dictionary for API responses
    def __todict__(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }
    
    # String representation of the User object for debugging purposes
    def __repr__(self):
        return f'<User {self.username}>'