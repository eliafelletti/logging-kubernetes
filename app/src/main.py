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