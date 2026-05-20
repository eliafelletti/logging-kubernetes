import pytest
from src.main import app as flask_app

@pytest.fixture
def client():
    '''Fixture to create a test client for the Flask application.'''
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test_secret_key'

    with flask_app.test_client() as testing_client:
        yield testing_client