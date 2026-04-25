import time
import uuid
import logging
import math
from flask import Flask, request, jsonify, render_template, g, has_request_context
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
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
    
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    ''' Log SQL queries for debugging, performance monitoring and SQL injection detection '''

    if has_request_context():
        ctx = getattr(g, 'log_context', {"system": "internal_request"})
    else:
        ctx = {"system": "start_up", "request_id": "internal-init", "path": "system_startup"}

    logger.info("🔍 Executing SQL Statement", extra={**ctx, "sql_query": statement, "sql_params": str(parameters)})


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
    ''' API endpoint to retrieve all users, with support for latency simulation '''

    delay = request.args.get('delay', default=0, type=int)
    if delay > 0:
        logger.warning(f"⏳ Simulating latency of {delay} seconds for testing purposes.", extra=g.log_context)
        time.sleep(delay)

    users = User.query.all()

    return jsonify([user.__todict__() for user in users]), 200


@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    ''' API endpoint to retrieve a specific user by ID '''

    # helpful method to get a user or return a 404 error if not found
    user = User.query.get_or_404(user_id)

    return jsonify(user.__todict__()), 200


@app.route('/api/user', methods=['POST'])
def create_user():
    ''' API endpoint to create a new user '''

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
        logger.error("❌ Errore database durante creazione utente", extra={**g.log_context, "db_error": str(e)})

        return jsonify({'error': 'Username or email already exists (or DB error)'}), 409
    
    
@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    ''' API endpoint to update an existing user's information '''

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
        logger.error("❌ Errore database durante aggiornamento utente", extra={**g.log_context, "db_error": str(e)})

        return jsonify({'error': 'Username or email already exists (or DB error)'}), 409
    
    
@app.route('/api/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    ''' API endpoint to delete a user by ID '''

    user = User.query.get_or_404(user_id)

    try:
        db.session.delete(user)
        db.session.commit()

        logger.warning(f"✅ User deleted successfully: {user.username}", extra={**g.log_context, "user_id": user.id})

        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback() # crucial for maintaining database integrity in case of errors -> resilient design
        logger.error("❌ Errore database durante eliminazione utente", extra={**g.log_context, "db_error": str(e)})

        return jsonify({'error': 'DB error during deletion'}), 500
    

'''
    Additional API endpoints for testing and observability
'''
@app.route('/api/health', methods=['GET'])
def health_check():
    ''' API endpoint for Kubernetes liveness and readiness probes '''
    try:
        # Simple DB query to check database connectivity
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": time.time()
        }), 200
    except Exception as e:
        logger.critical("🚨 HEALTH CHECK FAILED", extra={**g.log_context, "error": str(e)})
        
        return jsonify({"status": "unhealthy", "error": "Database unreachable"}), 503
    
    
@app.route('/api/panic', methods=['GET'])
def trigger_panic():
    ''' API endpoint to simulate a server crash '''
    logger.critical("🚨 PANIC endpoint triggered - simulating server crash!", extra=g.log_context)

    raise Exception("Simulated server crash for testing purposes")

    
@app.route('/api/log_storm', methods=['GET'])
def log_storm():
    ''' API endpoint to simulate a log storm for testing Loki ingestion capabilities '''
    count = request.args.get('count', default=100, type=int)

    logger.info(f"🌪️ Starting log storm: {count} lines", extra=g.log_context)

    for i in range(count):
        level = i % 3
        msg = f"Storm log sequence {i}/{count}"
        # Enrichment of logs with structured data for better observability and debugging in Grafana
        if level == 0:
            logger.info(f"🔹 {msg}", extra={**g.log_context, "storm_id": i})
        elif level == 1:
            logger.warning(f"⚠️ {msg}", extra={**g.log_context, "storm_id": i})
        else:
            logger.error(f"❌ {msg}", extra={**g.log_context, "storm_id": i, "fake_error_code": 500 + i})
            
    return jsonify({"message": f"Generati {count} log strutturati"}), 200


@app.route(('/api/stress_cpu'), methods=['GET'])
def stress_cpu():
    ''' API endpoint to simulate CPU stress for testing auto-scaling and performance monitoring '''
    duration = request.args.get('duration', default=5, type=int)
    end_time = time.time() + duration

    logger.warning(f"🔥 Starting CPU stress test for {duration} seconds", extra=g.log_context)

    while time.time() < end_time:
        _ = math.sqrt(math.factorial(1000)) # Computationally intensive task to simulate CPU load

    return jsonify({"message": f"CPU stress test completed after {duration} seconds"}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)