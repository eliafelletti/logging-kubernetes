import time
import uuid
import logging
import math
from flask import Flask, request, jsonify, render_template, g, has_request_context
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

# Used src.<module_name> to avoid circular imports and ensure proper initialization order 
from src.config import Config
from src.models import db, User
from src.logging_config import setup_logging    

'''
    Main application file for the Flask web application.
    This file initializes the Flask app, sets up the database, configures logging, and defines all routes and API endpoints.
    The application includes:
        - CRUD operations for user management
        - Health check endpoint for Kubernetes probes
        - Endpoints to simulate server crashes, log storms, and CPU stress for testing purposes
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
    Global error handler to ensure API always returns JSON instead of HTML
'''
@app.errorhandler(404)
def resource_not_found(e):
    logger.warning("⚠️ 404 Not Found triggered", extra=getattr(g, 'log_context', {}))
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    logger.warning("⚠️ 405 Method Not Allowed triggered", extra=getattr(g, 'log_context', {}))
    return jsonify({"error": "Method not allowed"}), 405


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

    raw_delay = request.args.get('delay', None)

    if raw_delay is not None:
        try:
            # Try to convert the delay parameter to an integer
            delay = int(raw_delay)

            # Check if the delay is within the allowed range (0-10 seconds)
            if delay < 0 or delay > 10:
                logger.warning(f"⚠️ Out of bound delay parameter received: {delay}. Ignoring.", extra=getattr(g, 'log_context', {}))
                return jsonify({'error': 'Delay parameter must be between 0 and 10'}), 400

            # If delay is valid and greater than 0, simulate latency
            if delay > 0:
                logger.warning(f"⏳ Simulating latency of {delay} seconds for testing purposes.", extra=getattr(g, 'log_context', {}))
                time.sleep(delay)

        except (ValueError, TypeError, OverflowError):
            # Catch any exceptions that occur during conversion and log a warning
            logger.warning(f"⚠️ Not Integer delay parameter received: {raw_delay}. Ignoring.", extra=getattr(g, 'log_context', {}))
            return jsonify({'error': 'Delay parameter must be an integer'}), 400

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
    raw_count = request.args.get('count', None)

    # Se il parametro non viene passato nell'URL, usiamo il valore di default 100
    if raw_count is None:
        count = 100
    else:
        try:
            # Tenta la conversione esplicita in intero
            count = int(raw_count)
            
            # Boundary check: evita numeri negativi o tempeste di log eccessive
            if count < 0 or count > 1000:
                logger.warning(f"⚠️ Out of bound count parameter received: {count}.", extra=getattr(g, 'log_context', {}))
                return jsonify({'error': 'Count parameter must be between 0 and 1000'}), 400

        except (ValueError, TypeError, OverflowError):
            # Cattura stringhe non valide ("abc"), float, NaN, Inf o interi giganti
            logger.warning(f"⚠️ Invalid count parameter type received: {raw_count}.", extra=getattr(g, 'log_context', {}))
            return jsonify({'error': 'Count parameter must be an integer'}), 400

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
    raw_duration = request.args.get('duration', None)

    if raw_duration is None:
        duration = 5
    else:
        try:
            duration = int(raw_duration)

            # Boundary check: limits 
            if duration < 1 or duration > 20:
                logger.warning(f"⚠️ Out of bound duration parameter received: {duration}.", extra=getattr(g, 'log_context', {}))
                return jsonify({'error': 'Duration parameter must be between 1 and 20 seconds'}), 400

        except (ValueError, TypeError, OverflowError):
            logger.warning(f"⚠️ Invalid duration parameter type received: {raw_duration}.", extra=getattr(g, 'log_context', {}))
            return jsonify({'error': 'Duration parameter must be an integer'}), 400
    end_time = time.time() + duration

    logger.warning(f"🔥 Starting CPU stress test for {duration} seconds", extra=g.log_context)

    while time.time() < end_time:
        _ = sum(i**2 for i in range(10000)) # Computationally intensive task to simulate CPU load

    return jsonify({"message": f"CPU stress test completed after {duration} seconds"}), 200


# Run the Flask application in debug mode on all interfaces (werkzeug), listening on port 5000. 
# In production, this will be overridden by Gunicorn as specified in the Dockerfile.
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# When running with Gunicorn, the application will be served with multiple workers and proper logging configuration as defined in the Dockerfile.
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')

    # Use the same JSON formatter for Gunicorn retrieved from the logger configured in logging_config.py
    my_json_formatter = logger.handlers[0].formatter

    # Set the same JSON formatter for all Gunicorn handlers to ensure consistent log formatting across the application and Gunicorn
    for handler in gunicorn_logger.handlers:
        handler.setFormatter(my_json_formatter)

    # Ensure that the log level of the application logger matches the Gunicorn logger to avoid missing logs due to level mismatches
    logger.handlers = gunicorn_logger.handlers
    logger.setLevel(gunicorn_logger.level)

    logger.info('🚀 Flask application running with Gunicorn', extra={"system": "app_startup", "request_id": "internal-init", "path": "app_initialization"})
    logger.info("🚀 Flask application initialized and ready to serve requests.", extra={"system": "app_startup", "request_id": "internal-init", "path": "app_initialization"})
