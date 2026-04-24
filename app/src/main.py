import time
import uuid
import logging
from flask import Flask, request, jsonify, render_template, g
from config import Config
from models import db, User
from logging_config import setup_logging    

'''
    Main comment...TODO
'''

'''
    Initialization of the Flask application, database, and logging configuration. 
'''
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
logger = setup_logging()

with app.app_context():
    try:
        db.create_all()
        logger.info("✅ Database tables created successfully.")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")


'''
    Middleware for observability
'''
@app.before_request
def start_timer():
    ''' Start a timer to measure request processing time and generate a unique request ID for tracing in logs '''
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())) 

    # Prepare log context for structured logging
    g.log_context = {
        'request_id': g.request_id,
        'method': request.method,
        'path': request.path,
        'ip': request.remote_addr
    }
    logger.info(f"➡️ Incoming request: {request.method} {request.path}", extra=g.log_context)

@app.after_request
def log_response(response):
    ''' Log the response details along with the processing time '''
    if hasattr(g, 'start_time'):
        latency = time.time() - g.start_time
        g.log_context['latency_ms'] = round(latency * 1000, 2)  # Convert to milliseconds
        g.log_context['status_code'] = response.status_code
        logger.info(f"⬅️ Response sent: {response.status_code}", extra=g.log_context)

        # Include request ID in response headers for tracing
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')  

        return response
    else:
        logger.warning("⚠️ No start time found for request, cannot calculate latency.")
        return response
    
    
'''
    Route definitions
'''
@app.route('/')
def index():
    ''' Render the index page '''
    return render_template('index.html')


'''
    API CRUD endpoints for user management
'''
@app.route('/api/users', methods=['GET'])
def get_users():
    ''' API endpoint to retrieve all users, with support for latency simulation'''
    delay = request.args.get('delay', default=0, type=int)
    if delay > 0:
        logger.warning(f"⏳ Simulating latency of {delay} seconds for testing purposes.", extra=g.log_context)
        time.sleep(delay)

    users = User.query.all()

    return jsonify([user.__todict__() for user in users]), 200

@app.route('api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    ''' API endpoint to retrieve a specific user by ID'''
    # helpful method to get a user or return a 404 error if not found
    user = User.query.get_or_404(user_id)

    return jsonify(user.__todict__()), 200

@app.route('/api/user', methods=['POST'])
def create_user():
    ''' API endpoint to create a new user'''
    data = request.json

    if not data or 'username' not in data or 'email' not in data:
        logger.error("❌ Invalid request data: 'username' and 'email' are required.", extra=g.log_context)

        return jsonify({'error': 'Invalid request, username and email are required'}), 400
    
    try:
        new_user = User(username=data['username'], email=data['email'])
        db.session.add(new_user)
        db.session.commit()

        logger.info(f"✅ User created successfully: {new_user.username}", extra={**g.log_context, "user_id": new_user.id})

        return jsonify(new_user.__todict__()), 201
    except Exception as e:
        db.session.rollback() # crucial for maintaining database integrity in case of errors -> resilient design
        logger.error("Errore database durante creazione utente", extra={**g.log_context, "db_error": str(e)})

        return jsonify({'error': 'Username or email already exists (or DB error)'}), 409
    
@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    ''' API endpoint to update an existing user's information'''
    user = User.query.get_or_404(user_id)
    data = request.json

    if not data:
        logger.error("❌ No data provided for update.", extra=g.log_context)

        return jsonify({'error': 'No data provided'}), 400
    
    try:
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']

        db.session.commit()

        logger.info(f"✅ User updated successfully: {user.username}", extra={**g.log_context, "user_id": user.id})

        return jsonify(user.__todict__()), 200
    except Exception as e:
        db.session.rollback() # crucial for maintaining database integrity in case of errors -> resilient design
        logger.error("Errore database durante aggiornamento utente", extra={**g.log_context, "db_error": str(e)})

        return jsonify({'error': 'Username or email already exists (or DB error)'}), 409
    
@app.route('/api/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    ''' API endpoint to delete a user by ID'''
    user = User.query.get_or_404(user_id)

    try:
        db.session.delete(user)
        db.session.commit()

        logger.warning(f"✅ User deleted successfully: {user.username}", extra={**g.log_context, "user_id": user.id})

        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback() # crucial for maintaining database integrity in case of errors -> resilient design
        logger.error("Errore database durante eliminazione utente", extra={**g.log_context, "db_error": str(e)})

        return jsonify({'error': 'DB error during deletion'}), 500