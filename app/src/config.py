import os

'''
    Configuration class for the Flask application. This class loads database connection parameters and other settings from environment variables, 
    providing default values if they are not set. The SQLAlchemy connection string is constructed using the provided database parameters, 
    allowing the application to connect to a PostgreSQL database. Additionally, a secret key is defined for session management and security purposes.
'''

def get_env_variable(name: str) -> str:
    """Helper function to get environment variables with error handling."""
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"❌ Environment variable '{name}' is not set.")
    return value

class Config:
    # Database configuration for standard PostgreSQL connection parameters with defaults
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'users_db')

    # Load sensitive information from environment variables with error handling
    DB_PASSWORD = get_env_variable('DB_PASSWORD')
    SECRET_KEY = get_env_variable('SECRET_KEY')

    # SQLAlchemy connection string
    # Format: postgresql://username:password@host:port/database
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

