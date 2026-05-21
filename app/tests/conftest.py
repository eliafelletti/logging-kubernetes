import pytest
from src.config import Config
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use in-memory SQLite database for testing

from src.main import app as flask_app
from src.models import db

@pytest.fixture
def client():
    '''Fixture to create a test client for the Flask application and keep context for testing.'''
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test_secret_key'

    with flask_app.app_context():
        db.create_all()  # create tables in the in-memory database

        with flask_app.test_client() as testing_client:
            yield testing_client

        db.session.remove()  # clean up the session after tests
        db.drop_all()  # drop tables after tests