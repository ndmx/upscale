from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, g, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException, NotFound, Forbidden, InternalServerError, BadRequest, TooManyRequests
from datetime import datetime, timedelta
from functools import wraps
import requests as http_requests
import os
import json
import re
import secrets
import logging
from logging.handlers import RotatingFileHandler
import time
import hashlib

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

app = Flask(__name__)

# Security Configuration - Use environment variables in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Database URL handling (Railway/Render use postgres:// but SQLAlchemy needs postgresql://)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///upskill.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
app.config['PAYSTACK_SECRET_KEY'] = os.environ.get('PAYSTACK_SECRET_KEY', 'your_paystack_secret_key')

# Session Security
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# CSRF Protection
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

# Rate Limiting Configuration
app.config['RATELIMIT_STORAGE_URL'] = 'memory://'
app.config['RATELIMIT_DEFAULT'] = '200 per day, 50 per hour'
app.config['RATELIMIT_HEADERS_ENABLED'] = True

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler(
    'logs/upskill.log',
    maxBytes=10240000,
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Upskill Institute Application Startup')

# ============================================================================
# EXTENSIONS INITIALIZATION
# ============================================================================

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
login_manager.session_protection = 'strong'

# CSRF Protection
csrf = None
CSRFError = None
try:
    from flask_wtf.csrf import CSRFProtect, CSRFError as _CSRFError
    csrf = CSRFProtect(app)
    CSRFError = _CSRFError
except ImportError:
    app.logger.warning('Flask-WTF not installed. CSRF protection disabled.')

# Rate Limiting
limiter = None
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )
except ImportError:
    app.logger.warning('Flask-Limiter not installed. Rate limiting disabled.')

# Security Headers (Talisman)
try:
    from flask_talisman import Talisman
    if os.environ.get('FLASK_ENV') == 'production':
        talisman = Talisman(
            app,
            force_https=True,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            content_security_policy={
                'default-src': "'self'",
                'script-src': ["'self'", 'cdn.jsdelivr.net', "'unsafe-inline'"],
                'style-src': ["'self'", 'cdn.jsdelivr.net', "'unsafe-inline'"],
                'font-src': ["'self'", 'cdn.jsdelivr.net'],
                'img-src': ["'self'", 'data:', 'https:'],
            },
        )
except ImportError:
    app.logger.warning('Flask-Talisman not installed. Security headers limited.')

# Input Sanitization
bleach = None
try:
    import bleach as _bleach
    bleach = _bleach
except ImportError:
    app.logger.warning('Bleach not installed. Input sanitization limited.')

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_input(text):
    """Sanitize user input to prevent XSS attacks"""
    if text is None:
        return None
    if not isinstance(text, str):
        return text
    if bleach:
        text = bleach.clean(text, tags=[], strip=True)
    text = text.strip()
    return text

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) and len(email) <= 254

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password is too long."
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter."
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number."
    return True, "Valid password."

def validate_name(name):
    """Validate user name"""
    if not name or len(name) < 2:
        return False, "Name must be at least 2 characters."
    if len(name) > 100:
        return False, "Name is too long."
    if not re.match(r"^[A-Za-z\s\-']+$", name):
        return False, "Name contains invalid characters."
    return True, "Valid name."

def get_client_ip():
    """Get client IP address, handling proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def generate_session_id():
    """Generate a secure session ID"""
    return secrets.token_urlsafe(32)

def hash_for_logging(sensitive_data):
    """Hash sensitive data for safe logging"""
    return hashlib.sha256(str(sensitive_data).encode()).hexdigest()[:16]

def is_safe_url(target):
    """Validate redirect URL for open redirect prevention"""
    from urllib.parse import urlparse, urljoin
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# ============================================================================
# SECURITY MIDDLEWARE
# ============================================================================

@app.before_request
def before_request():
    """Security checks before each request"""
    g.start_time = time.time()
    g.request_id = secrets.token_hex(8)
    
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        abort(413)
    
    app.logger.info(f'[{g.request_id}] {request.method} {request.path} from {hash_for_logging(get_client_ip())}')

@app.after_request
def after_request(response):
    """Add security headers and log response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    if 'Cache-Control' not in response.headers:
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        else:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    
    if hasattr(g, 'start_time'):
        duration = (time.time() - g.start_time) * 1000
        if duration > 1000:
            app.logger.warning(f'[{g.request_id}] Slow request: {duration:.2f}ms')
    
    return response

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(400)
def bad_request_error(error):
    app.logger.warning(f'Bad Request: {request.url} - {str(error)}')
    return render_template('errors/400.html', error=error), 400

@app.errorhandler(403)
def forbidden_error(error):
    app.logger.warning(f'Forbidden: {request.url}')
    return render_template('errors/403.html', error=error), 403

@app.errorhandler(404)
def not_found_error(error):
    app.logger.info(f'Not Found: {request.url}')
    return render_template('errors/404.html', error=error), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    app.logger.warning(f'Request Too Large: {request.url}')
    return render_template('errors/413.html', error=error), 413

@app.errorhandler(429)
def ratelimit_handler(error):
    app.logger.warning(f'Rate Limit Exceeded: {request.url} from {hash_for_logging(get_client_ip())}')
    return render_template('errors/429.html', error=error), 429

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'Server Error: {request.url} - {str(error)}', exc_info=True)
    return render_template('errors/500.html', error=error), 500

# CSRF Error Handler - only register if CSRF is available
if csrf and CSRFError:
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """Handle CSRF errors"""
        app.logger.warning(f'CSRF Error: {request.url} from {hash_for_logging(get_client_ip())}')
        flash('Your session has expired. Please try again.', 'warning')
        return redirect(request.referrer or url_for('home'))

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions"""
    if isinstance(error, HTTPException):
        return error
    app.logger.error(f'Unhandled Exception: {str(error)}', exc_info=True)
    db.session.rollback()
    return render_template('errors/500.html', error=error), 500

# ============================================================================
# MODELS
# ============================================================================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password = db.Column(db.String(256), nullable=False)
    payment_plan = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    payments = db.relationship('Payment', backref='user', lazy=True)
    
    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def increment_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
    
    def reset_failed_login(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.utcnow()
        db.session.commit()

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), unique=True, index=True)
    amount = db.Column(db.Integer)
    status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    modules = db.relationship('Module', backref='course', lazy=True)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), index=True)
    progresses = db.relationship('Progress', backref='module', lazy=True)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), index=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'module_id', name='unique_user_module'),
    )

class QuestionnaireResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    experience_level = db.Column(db.String(50))
    interests = db.Column(db.Text)
    goals = db.Column(db.Text)
    current_skills = db.Column(db.Text)
    learning_style = db.Column(db.String(100))
    time_commitment = db.Column(db.String(50))
    recommended_course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    match_percentage = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    
    recommended_course = db.relationship('Course', backref='questionnaire_responses', lazy=True)

class SecurityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def log_security_event(event_type, user_id=None, details=None):
    try:
        log = SecurityLog(
            event_type=event_type,
            user_id=user_id,
            ip_address=get_client_ip(),
            user_agent=request.headers.get('User-Agent', '')[:500],
            details=str(details)[:1000] if details else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        app.logger.error(f'Failed to log security event: {e}')

# ============================================================================
# USER LOADER
# ============================================================================

@login_manager.user_loader
def load_user(user_id):
    try:
        user = User.query.get(int(user_id))
        if user and user.is_active and not user.is_locked():
            return user
        return None
    except Exception:
        return None

@login_manager.unauthorized_handler
def unauthorized():
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('login', next=request.url))

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

with app.app_context():
    db.create_all()
    if Course.query.count() == 0:
        courses_data = [
            {"title": "Cybersecurity with AI", "description": "Forge unbreakable defenses blending timeless cybersecurity with AI wizardry - ready to shield global fintech giants from Lagos to London.", "modules": [
                {"title": "Intro to AI Threats", "content": "Explore how AI is weaponized in cyber attacks, including deepfakes and automated phishing tailored to local mobile banking vulnerabilities."},
                {"title": "Defensive AI Tools", "content": "Hands-on training with machine learning models for anomaly detection and threat prediction."},
                {"title": "Ethical AI in Security", "content": "Delve into AI biases in cybersecurity tools and ethical considerations for deployment."}
            ]},
            {"title": "Data Engineering for AI", "description": "Craft lightning-fast data pipelines for AI dominance - conquering spotty connections and unlocking insights that power startups from Accra to Austin.", "modules": [
                {"title": "ETL Basics for AI", "content": "Design extract, transform, load processes with AI automation."},
                {"title": "Cloud Integration and Scalability", "content": "Integrate cloud platforms like AWS or Azure with AI data needs."},
                {"title": "Data Governance with AI", "content": "Implement AI-assisted data quality checks and compliance."}
            ]},
            {"title": "Web App Development with AI", "description": "Revolutionize web creation with AI-infused builds that captivate users worldwide, resilient from Dakar downtime to Dubai demands.", "modules": [
                {"title": "React with AI APIs", "content": "Build full-stack web apps using React and integrate AI APIs."},
                {"title": "Deployment and Security", "content": "Deploy AI-integrated apps with emphasis on security."},
                {"title": "AI-Enhanced User Experiences", "content": "Create personalized web features using AI."}
            ]}
        ]
        for c in courses_data:
            course = Course(title=c["title"], description=c["description"])
            db.session.add(course)
            db.session.commit()
            for idx, m in enumerate(c["modules"]):
                module = Module(title=m["title"], content=m["content"], course_id=course.id, order=idx)
                db.session.add(module)
            db.session.commit()

# ============================================================================
# QUESTIONNAIRE DATA
# ============================================================================

QUESTIONNAIRE_QUESTIONS = [
    {"id": "q1", "section": "experience", "question": "What is your current level of tech experience?", "type": "single",
     "options": [
         {"value": "absolute_beginner", "label": "Complete beginner - No coding experience", "cyber": 0, "data": 0, "web": 0},
         {"value": "some_basics", "label": "Know some basics - HTML, Excel, basic computer skills", "cyber": 1, "data": 2, "web": 3},
         {"value": "intermediate", "label": "Intermediate - Can write simple programs", "cyber": 2, "data": 3, "web": 3},
         {"value": "advanced", "label": "Advanced - Professional experience in tech", "cyber": 3, "data": 3, "web": 3}
     ]},
    {"id": "q2", "section": "experience", "question": "Have you taken any programming or tech courses before?", "type": "single",
     "options": [
         {"value": "never", "label": "Never taken any", "cyber": 0, "data": 0, "web": 0},
         {"value": "online_tutorials", "label": "Online tutorials (YouTube, Udemy, etc.)", "cyber": 1, "data": 1, "web": 1},
         {"value": "bootcamp", "label": "Completed a bootcamp or formal course", "cyber": 2, "data": 2, "web": 2},
         {"value": "degree", "label": "Have a tech-related degree", "cyber": 3, "data": 3, "web": 2}
     ]},
    {"id": "q3", "section": "experience", "question": "Which tools/technologies have you used?", "type": "multiple",
     "options": [
         {"value": "excel_data", "label": "Excel/Google Sheets for data analysis", "cyber": 0, "data": 3, "web": 0},
         {"value": "python", "label": "Python", "cyber": 2, "data": 3, "web": 2},
         {"value": "javascript", "label": "JavaScript", "cyber": 1, "data": 1, "web": 3},
         {"value": "databases", "label": "SQL/Databases", "cyber": 1, "data": 3, "web": 2},
         {"value": "security_tools", "label": "Security tools (antivirus, VPNs)", "cyber": 3, "data": 0, "web": 0},
         {"value": "none", "label": "None of these", "cyber": 0, "data": 0, "web": 0}
     ]},
    {"id": "q4", "section": "interests", "question": "What aspect of technology excites you most?", "type": "single",
     "options": [
         {"value": "protecting_systems", "label": "Protecting systems and fighting cybercrime", "cyber": 5, "data": 0, "web": 0},
         {"value": "analyzing_data", "label": "Analyzing data and finding patterns", "cyber": 0, "data": 5, "web": 1},
         {"value": "building_apps", "label": "Building websites and mobile apps", "cyber": 0, "data": 1, "web": 5},
         {"value": "ai_ml", "label": "AI and machine learning", "cyber": 2, "data": 4, "web": 2}
     ]},
    {"id": "q5", "section": "interests", "question": "Which work environment appeals to you?", "type": "single",
     "options": [
         {"value": "security_operations", "label": "Security operations center, monitoring threats", "cyber": 5, "data": 0, "web": 0},
         {"value": "data_analysis", "label": "Working with large datasets and analytics", "cyber": 0, "data": 5, "web": 0},
         {"value": "creative_design", "label": "Creative design and user interfaces", "cyber": 0, "data": 0, "web": 5},
         {"value": "problem_solving", "label": "Solving complex technical problems", "cyber": 3, "data": 3, "web": 3}
     ]},
    {"id": "q6", "section": "interests", "question": "What type of problems do you enjoy solving?", "type": "single",
     "options": [
         {"value": "security_puzzles", "label": "Security puzzles and vulnerabilities", "cyber": 5, "data": 1, "web": 1},
         {"value": "data_insights", "label": "Finding insights from data", "cyber": 1, "data": 5, "web": 1},
         {"value": "user_experience", "label": "Creating great user experiences", "cyber": 0, "data": 1, "web": 5},
         {"value": "system_architecture", "label": "Designing system architecture", "cyber": 2, "data": 3, "web": 3}
     ]},
    {"id": "q7", "section": "interests", "question": "What's your long-term career vision?", "type": "single",
     "options": [
         {"value": "security_specialist", "label": "Become a security specialist or ethical hacker", "cyber": 5, "data": 0, "web": 0},
         {"value": "data_scientist", "label": "Data scientist or ML engineer", "cyber": 0, "data": 5, "web": 0},
         {"value": "fullstack_dev", "label": "Full-stack developer or tech lead", "cyber": 0, "data": 1, "web": 5},
         {"value": "tech_entrepreneur", "label": "Start my own tech company", "cyber": 1, "data": 2, "web": 4}
     ]},
    {"id": "q8", "section": "skills", "question": "Which skills are you most confident in?", "type": "multiple",
     "options": [
         {"value": "networking", "label": "Computer networking basics", "cyber": 3, "data": 1, "web": 1},
         {"value": "programming", "label": "Programming/coding", "cyber": 2, "data": 3, "web": 3},
         {"value": "data_analysis", "label": "Data analysis", "cyber": 1, "data": 3, "web": 1},
         {"value": "web_design", "label": "Web design/HTML/CSS", "cyber": 0, "data": 0, "web": 3},
         {"value": "problem_solving", "label": "Logical problem-solving", "cyber": 2, "data": 3, "web": 2},
         {"value": "none_yet", "label": "Still building these skills", "cyber": 0, "data": 0, "web": 0}
     ]},
    {"id": "q9", "section": "skills", "question": "How do you prefer to learn?", "type": "single",
     "options": [
         {"value": "hands_on", "label": "Hands-on projects and real-world practice", "cyber": 2, "data": 2, "web": 3},
         {"value": "theory_first", "label": "Understanding theory before practice", "cyber": 3, "data": 3, "web": 1},
         {"value": "video_tutorials", "label": "Video tutorials and visual learning", "cyber": 1, "data": 2, "web": 2},
         {"value": "mixed", "label": "Combination of all approaches", "cyber": 2, "data": 2, "web": 2}
     ]},
    {"id": "q10", "section": "skills", "question": "How many hours per week can you commit to learning?", "type": "single",
     "options": [
         {"value": "less_5", "label": "Less than 5 hours", "cyber": 0, "data": 0, "web": 0},
         {"value": "5_10", "label": "5-10 hours", "cyber": 1, "data": 1, "web": 1},
         {"value": "10_20", "label": "10-20 hours", "cyber": 2, "data": 2, "web": 2},
         {"value": "20_plus", "label": "20+ hours (full-time)", "cyber": 3, "data": 3, "web": 3}
     ]},
    {"id": "q11", "section": "skills", "question": "What's your approach to technical challenges?", "type": "single",
     "options": [
         {"value": "detective", "label": "Like a detective - investigate and find vulnerabilities", "cyber": 5, "data": 2, "web": 1},
         {"value": "analyst", "label": "Analyze patterns and optimize solutions", "cyber": 1, "data": 5, "web": 2},
         {"value": "builder", "label": "Build and create solutions from scratch", "cyber": 1, "data": 2, "web": 5},
         {"value": "researcher", "label": "Research best practices and implement them", "cyber": 3, "data": 3, "web": 3}
     ]},
    {"id": "q12", "section": "goals", "question": "What type of role are you targeting?", "type": "single",
     "options": [
         {"value": "security_analyst", "label": "Cybersecurity Analyst / Penetration Tester", "cyber": 5, "data": 0, "web": 0},
         {"value": "data_engineer", "label": "Data Engineer / Data Analyst", "cyber": 0, "data": 5, "web": 0},
         {"value": "web_developer", "label": "Web Developer / Software Engineer", "cyber": 0, "data": 1, "web": 5},
         {"value": "ml_engineer", "label": "ML Engineer / AI Specialist", "cyber": 1, "data": 5, "web": 1}
     ]},
    {"id": "q13", "section": "goals", "question": "Which industry interests you most?", "type": "single",
     "options": [
         {"value": "fintech", "label": "Fintech (Paystack, Flutterwave, banks)", "cyber": 4, "data": 3, "web": 3},
         {"value": "cybersecurity", "label": "Cybersecurity firms", "cyber": 5, "data": 1, "web": 0},
         {"value": "tech_startups", "label": "Tech startups and product companies", "cyber": 2, "data": 3, "web": 5},
         {"value": "ecommerce", "label": "E-commerce and digital platforms", "cyber": 2, "data": 3, "web": 4}
     ]},
    {"id": "q14", "section": "goals", "question": "What salary range are you targeting? (Monthly in Naira)", "type": "single",
     "options": [
         {"value": "entry", "label": "₦150,000 - ₦300,000 (Entry level)", "cyber": 1, "data": 1, "web": 1},
         {"value": "mid", "label": "₦300,000 - ₦600,000 (Mid-level)", "cyber": 2, "data": 2, "web": 2},
         {"value": "senior", "label": "₦600,000 - ₦1,000,000 (Senior)", "cyber": 3, "data": 3, "web": 3},
         {"value": "lead", "label": "₦1,000,000+ (Lead/Principal)", "cyber": 3, "data": 3, "web": 3}
     ]},
    {"id": "q15", "section": "goals", "question": "Where do you prefer to work?", "type": "single",
     "options": [
         {"value": "lagos", "label": "Lagos, Nigeria", "cyber": 2, "data": 2, "web": 2},
         {"value": "accra", "label": "Accra, Ghana", "cyber": 1, "data": 1, "web": 2},
         {"value": "remote", "label": "Remote from anywhere", "cyber": 2, "data": 3, "web": 3},
         {"value": "flexible", "label": "Flexible / Open to relocation", "cyber": 2, "data": 2, "web": 2}
     ]},
    {"id": "q16", "section": "goals", "question": "What motivates you to upskill now?", "type": "single",
     "options": [
         {"value": "career_change", "label": "Career change into tech", "cyber": 2, "data": 2, "web": 2},
         {"value": "job_security", "label": "Job security and better opportunities", "cyber": 3, "data": 2, "web": 2},
         {"value": "passion", "label": "Passion for technology and innovation", "cyber": 2, "data": 2, "web": 3},
         {"value": "entrepreneurship", "label": "Start my own tech business", "cyber": 1, "data": 2, "web": 4}
     ]}
]

JOB_DATABASE = {
    "Cybersecurity with AI": {
        "jobs": [
            {"title": "Cybersecurity Analyst", "description": "Monitor and protect systems from threats", "salary_range": "₦200,000 - ₦600,000/month", "skills": ["Network Security", "Threat Analysis", "SIEM Tools"]},
            {"title": "Penetration Tester", "description": "Test systems for vulnerabilities", "salary_range": "₦300,000 - ₦800,000/month", "skills": ["Penetration Testing", "Security Tools", "Python"]},
            {"title": "SOC Analyst", "description": "24/7 monitoring of security events", "salary_range": "₦250,000 - ₦700,000/month", "skills": ["Security Monitoring", "Log Analysis", "Automation"]}
        ],
        "companies": ["Flutterwave", "Paystack", "Interswitch", "MTN", "Access Bank", "GT Bank"]
    },
    "Data Engineering for AI": {
        "jobs": [
            {"title": "Data Engineer", "description": "Build and maintain data pipelines", "salary_range": "₦300,000 - ₦900,000/month", "skills": ["ETL Pipelines", "SQL", "Python", "Cloud"]},
            {"title": "ML Engineer", "description": "Develop and deploy ML models", "salary_range": "₦400,000 - ₦1,200,000/month", "skills": ["Machine Learning", "Python", "TensorFlow"]},
            {"title": "Analytics Engineer", "description": "Transform raw data into insights", "salary_range": "₦250,000 - ₦700,000/month", "skills": ["SQL", "Data Visualization", "Python"]}
        ],
        "companies": ["Flutterwave", "Paystack", "Andela", "Kuda Bank", "PiggyVest"]
    },
    "Web App Development with AI": {
        "jobs": [
            {"title": "Full-Stack Developer", "description": "Build complete web applications", "salary_range": "₦300,000 - ₦900,000/month", "skills": ["React", "Node.js", "APIs", "Databases"]},
            {"title": "Frontend Engineer", "description": "Create responsive UIs", "salary_range": "₦250,000 - ₦700,000/month", "skills": ["React/Vue", "JavaScript", "CSS"]},
            {"title": "Backend Developer", "description": "Build APIs and services", "salary_range": "₦300,000 - ₦850,000/month", "skills": ["Python/Node.js", "APIs", "Databases"]}
        ],
        "companies": ["Andela", "Flutterwave", "Paystack", "Kuda Bank", "Jumia", "Bolt"]
    }
}

# ============================================================================
# RECOMMENDATION ENGINE
# ============================================================================

def calculate_course_recommendation(responses):
    """Calculate which course best matches user responses"""
    scores = {'Cybersecurity with AI': 0, 'Data Engineering for AI': 0, 'Web App Development with AI': 0}
    
    for question_id, answer in responses.items():
        question = next((q for q in QUESTIONNAIRE_QUESTIONS if q['id'] == question_id), None)
        if not question:
            continue
        if question['type'] == 'single':
            option = next((opt for opt in question['options'] if opt['value'] == answer), None)
            if option:
                scores['Cybersecurity with AI'] += option.get('cyber', 0)
                scores['Data Engineering for AI'] += option.get('data', 0)
                scores['Web App Development with AI'] += option.get('web', 0)
        elif question['type'] == 'multiple' and isinstance(answer, list):
            for ans_value in answer:
                option = next((opt for opt in question['options'] if opt['value'] == ans_value), None)
                if option:
                    scores['Cybersecurity with AI'] += option.get('cyber', 0)
                    scores['Data Engineering for AI'] += option.get('data', 0)
                    scores['Web App Development with AI'] += option.get('web', 0)
    
    max_score = max(scores.values())
    if max_score == 0:
        recommended_course = 'Web App Development with AI'
        match_percentage = 60
    else:
        recommended_course = max(scores, key=scores.get)
        total_possible = len(QUESTIONNAIRE_QUESTIONS) * 5
        match_percentage = min(int((max_score / total_possible) * 100), 99)
    
    return recommended_course, match_percentage, scores

def recommend_module(user_id, course_id):
    """Recommend next module for user - BUG 2 FIXED: counts only this course's modules"""
    try:
        modules = Module.query.filter_by(course_id=course_id).order_by(Module.order, Module.id).all()
        module_ids = [m.id for m in modules]
        
        # Count completed modules only for THIS course
        completed = Progress.query.filter(
            Progress.user_id == user_id,
            Progress.module_id.in_(module_ids),
            Progress.completed == True
        ).count()
        
        if completed < len(modules):
            return modules[completed]
        return None
    except Exception as e:
        app.logger.error(f'Error recommending module: {e}')
        return None

# ============================================================================
# ROUTES - PUBLIC
# ============================================================================

@app.route('/')
def home():
    try:
        courses = Course.query.filter_by(is_active=True).all()
        return render_template('index.html', courses=courses)
    except Exception as e:
        app.logger.error(f'Error loading home page: {e}')
        return render_template('index.html', courses=[])

@app.route('/courses')
def courses():
    try:
        all_courses = Course.query.filter_by(is_active=True).all()
        return render_template('courses.html', courses=all_courses)
    except Exception as e:
        app.logger.error(f'Error loading courses: {e}')
        return render_template('courses.html', courses=[])

@app.route('/about')
def about():
    """Showcase mission, pillars, and credibility signals."""
    return render_template('about.html')

# Course content data for detail pages
COURSE_CONTENT = {
    "Cybersecurity with AI": {
        "highlights": [
            "Detect and respond to AI-powered cyber attacks including deepfakes and automated phishing",
            "Build intelligent defense systems using machine learning for threat detection",
            "Master ethical hacking techniques adapted for local fintech vulnerabilities",
            "Implement AI-driven security monitoring for real-time threat prevention",
            "Understand compliance frameworks (NDPA, GDPR) for data protection",
            "Design secure architectures for mobile banking and payment systems"
        ],
        "prerequisites": [
            "Basic computer literacy and internet navigation skills",
            "Understanding of how networks and the internet work (helpful but not required)",
            "Curiosity about security and protecting digital systems"
        ],
        "curriculum": [
            ("Week 1-2", "Foundations of Cybersecurity & AI Threat Landscape"),
            ("Week 3-4", "Network Security & Vulnerability Assessment"),
            ("Week 5-6", "AI-Powered Attack Detection & Prevention"),
            ("Week 7-8", "Ethical Hacking & Penetration Testing"),
            ("Week 9-10", "Security Operations Center (SOC) & Incident Response"),
            ("Week 11-12", "Capstone Project: Secure a Fintech Application")
        ]
    },
    "Data Engineering for AI": {
        "highlights": [
            "Design and build scalable ETL pipelines for AI/ML workflows",
            "Master Python, SQL, and cloud platforms (AWS/Azure) for data infrastructure",
            "Implement data quality checks and governance with AI automation",
            "Build real-time data processing systems for e-commerce and fintech",
            "Create data lakes and warehouses optimized for machine learning",
            "Handle local challenges: intermittent connectivity and diverse data sources"
        ],
        "prerequisites": [
            "Basic understanding of spreadsheets (Excel/Google Sheets)",
            "Familiarity with basic programming concepts (any language)",
            "Interest in working with data and building systems"
        ],
        "curriculum": [
            ("Week 1-2", "Python for Data Engineering & SQL Fundamentals"),
            ("Week 3-4", "ETL Pipeline Design & Apache Airflow"),
            ("Week 5-6", "Cloud Data Platforms (AWS/Azure)"),
            ("Week 7-8", "Data Warehousing & Data Lakes"),
            ("Week 9-10", "Real-time Processing & Stream Analytics"),
            ("Week 11-12", "Capstone Project: Build an AI-Ready Data Pipeline")
        ]
    },
    "Web App Development with AI": {
        "highlights": [
            "Build full-stack web applications with React, Node.js, and Python",
            "Integrate AI APIs (OpenAI, Google AI) for intelligent features",
            "Create chatbots, recommendation engines, and personalized experiences",
            "Deploy production applications with CI/CD and security best practices",
            "Design mobile-first, accessible interfaces for local users",
            "Implement offline capabilities for low-connectivity environments"
        ],
        "prerequisites": [
            "Basic HTML and CSS knowledge (helpful but we cover fundamentals)",
            "Understanding of how websites work",
            "Enthusiasm for building user-facing applications"
        ],
        "curriculum": [
            ("Week 1-2", "Modern JavaScript & React Fundamentals"),
            ("Week 3-4", "Backend Development with Node.js/Python"),
            ("Week 5-6", "Database Design & API Development"),
            ("Week 7-8", "AI Integration: Chatbots & Recommendations"),
            ("Week 9-10", "Deployment, Security & Performance"),
            ("Week 11-12", "Capstone Project: AI-Powered Web Application")
        ]
    }
}

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    if course_id < 1 or course_id > 1000000:
        abort(404)
    course = Course.query.filter_by(id=course_id, is_active=True).first_or_404()
    
    # Get course-specific content
    content = COURSE_CONTENT.get(course.title, {})
    
    return render_template('course_detail.html', 
                         course=course,
                         highlights=content.get('highlights', []),
                         prerequisites=content.get('prerequisites', []),
                         curriculum=content.get('curriculum', []))

# ============================================================================
# ROUTES - AUTHENTICATION
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = sanitize_input(request.form.get('name', ''))
        email = sanitize_input(request.form.get('email', '').lower().strip())
        password = request.form.get('password', '')
        
        name_valid, name_msg = validate_name(name)
        if not name_valid:
            flash(name_msg, 'error')
            return render_template('register.html')
        
        if not validate_email(email):
            flash('Please enter a valid email address.', 'error')
            return render_template('register.html')
        
        password_valid, password_msg = validate_password(password)
        if not password_valid:
            flash(password_msg, 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            log_security_event('registration_duplicate_email', details=email)
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')
        
        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256:600000')
            user = User(name=name, email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            log_security_event('registration_success', user_id=user.id)
            login_user(user)
            flash('Welcome to Upskill! Your account has been created.', 'success')
            return redirect(url_for('enroll'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Registration error: {e}')
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = sanitize_input(request.form.get('email', '').lower().strip())
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            if user.is_locked():
                log_security_event('login_locked_account', user_id=user.id)
                flash('Account temporarily locked. Please try again later.', 'error')
                return render_template('login.html')
            
            if check_password_hash(user.password, password):
                if not user.is_active:
                    flash('Your account has been deactivated.', 'error')
                    return render_template('login.html')
                
                user.reset_failed_login()
                login_user(user)
                log_security_event('login_success', user_id=user.id)
                
                next_page = request.args.get('next')
                if next_page and is_safe_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            else:
                user.increment_failed_login()
                log_security_event('login_failed', user_id=user.id)
        else:
            log_security_event('login_unknown_email', details=hash_for_logging(email))
        
        flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_security_event('logout', user_id=current_user.id)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# ============================================================================
# ROUTES - PROTECTED
# ============================================================================

@app.route('/enroll', methods=['GET', 'POST'])
@login_required
def enroll():
    if request.method == 'POST':
        payment_plan = sanitize_input(request.form.get('payment', ''))
        
        if payment_plan not in ['full', 'monthly']:
            flash('Invalid payment plan selected.', 'error')
            return render_template('enroll.html')
        
        amount = 15000000 if payment_plan == 'full' else 5000000
        current_user.payment_plan = payment_plan
        
        try:
            db.session.commit()
            reference = f'upskill_{current_user.id}_{secrets.token_hex(16)}'
            
            headers = {'Authorization': f'Bearer {app.config["PAYSTACK_SECRET_KEY"]}', 'Content-Type': 'application/json'}
            data = {'email': current_user.email, 'amount': amount, 'reference': reference, 'callback_url': url_for('payment_callback', _external=True)}
            
            response = http_requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                resp_data = response.json()
                if resp_data.get('status'):
                    payment = Payment(reference=reference, amount=amount, status='pending', user_id=current_user.id)
                    db.session.add(payment)
                    db.session.commit()
                    log_security_event('payment_initiated', user_id=current_user.id, details=f'Amount: {amount}')
                    return redirect(resp_data['data']['authorization_url'])
            
            flash('Payment initialization failed. Please try again.', 'error')
        except http_requests.Timeout:
            flash('Payment service timeout. Please try again.', 'error')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Enrollment error: {e}')
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('enroll.html')

@app.route('/payment_callback')
@login_required
def payment_callback():
    reference = request.args.get('reference', '')
    
    if not reference or not reference.startswith('upskill_'):
        log_security_event('payment_invalid_reference', user_id=current_user.id)
        flash('Invalid payment reference.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        headers = {'Authorization': f'Bearer {app.config["PAYSTACK_SECRET_KEY"]}'}
        response = http_requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers, timeout=30)
        
        if response.status_code == 200:
            resp_data = response.json()
            if resp_data.get('status') and resp_data['data'].get('status') == 'success':
                payment = Payment.query.filter_by(reference=reference, user_id=current_user.id).first()
                if payment:
                    payment.status = 'success'
                    payment.verified_at = datetime.utcnow()
                    db.session.commit()
                    log_security_event('payment_success', user_id=current_user.id, details=reference)
                    flash('Payment successful!', 'success')
                    return redirect(url_for('dashboard'))
        
        flash('Payment verification failed.', 'error')
    except Exception as e:
        app.logger.error(f'Payment callback error: {e}')
        flash('Error verifying payment.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        courses = Course.query.filter_by(is_active=True).all()
        progresses = {p.module_id: p.completed for p in Progress.query.filter_by(user_id=current_user.id).all()}
        recommendations = {}
        for course in courses:
            rec = recommend_module(current_user.id, course.id)
            if rec:
                recommendations[course.id] = rec.title
        return render_template('dashboard.html', courses=courses, progresses=progresses, recommendations=recommendations, user=current_user)
    except Exception as e:
        app.logger.error(f'Dashboard error: {e}')
        flash('Error loading dashboard.', 'error')
        return redirect(url_for('home'))

@app.route('/module/<int:module_id>', methods=['GET', 'POST'])
@login_required
def view_module(module_id):
    if module_id < 1 or module_id > 1000000:
        abort(404)
    
    module = Module.query.get_or_404(module_id)
    progress = Progress.query.filter_by(user_id=current_user.id, module_id=module_id).first()
    
    if request.method == 'POST':
        try:
            if not progress:
                progress = Progress(user_id=current_user.id, module_id=module_id, completed=True, completed_at=datetime.utcnow())
                db.session.add(progress)
            else:
                progress.completed = True
                progress.completed_at = datetime.utcnow()
            db.session.commit()
            flash('Module completed!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Progress update error: {e}')
            flash('Error updating progress.', 'error')
    
    return render_template('module.html', module=module, completed=progress.completed if progress else False)

# ============================================================================
# ROUTES - QUESTIONNAIRE
# ============================================================================

@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html', questions=QUESTIONNAIRE_QUESTIONS)

@app.route('/questionnaire/submit', methods=['POST'])
def questionnaire_submit():
    """Process questionnaire - BUG 3 FIXED: consistent data handling"""
    try:
        responses = {}
        for question in QUESTIONNAIRE_QUESTIONS:
            q_id = question['id']
            if question['type'] == 'multiple':
                responses[q_id] = request.form.getlist(q_id)
            else:
                value = request.form.get(q_id)
                responses[q_id] = value  # Keep as None if not provided
        
        if len([v for v in responses.values() if v]) < 5:
            flash('Please answer more questions.', 'warning')
            return redirect(url_for('questionnaire'))
        
        recommended_course_name, match_percentage, _ = calculate_course_recommendation(responses)
        recommended_course = Course.query.filter_by(title=recommended_course_name).first()
        session_id = generate_session_id()
        
        # Store with consistent None for missing values
        questionnaire_response = QuestionnaireResponse(
            session_id=session_id,
            experience_level=responses.get('q1'),
            interests=json.dumps(responses.get('q4')) if responses.get('q4') else None,
            goals=json.dumps(responses.get('q12')) if responses.get('q12') else None,
            current_skills=json.dumps(responses.get('q8', [])),
            learning_style=responses.get('q9'),
            time_commitment=responses.get('q10'),
            recommended_course_id=recommended_course.id if recommended_course else None,
            match_percentage=match_percentage,
            ip_address=get_client_ip()
        )
        db.session.add(questionnaire_response)
        db.session.commit()
        return redirect(url_for('questionnaire_results', session_id=session_id))
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Questionnaire error: {e}')
        flash('An error occurred.', 'error')
        return redirect(url_for('questionnaire'))

@app.route('/results/<session_id>')
def questionnaire_results(session_id):
    if not session_id or len(session_id) > 100 or not re.match(r'^[A-Za-z0-9_-]+$', session_id):
        abort(404)
    
    response = QuestionnaireResponse.query.filter_by(session_id=session_id).first_or_404()
    course = response.recommended_course
    
    if not course:
        flash('Unable to find recommended course.', 'error')
        return redirect(url_for('questionnaire'))
    
    job_data = JOB_DATABASE.get(course.title, {})
    return render_template('questionnaire_results.html', course=course, match_percentage=response.match_percentage, jobs=job_data.get('jobs', []), companies=job_data.get('companies', []))

# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/health')
def health_check():
    try:
        db.session.execute(db.text('SELECT 1'))
        return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500

@app.route('/robots.txt')
def robots():
    content = "User-agent: *\nAllow: /\nDisallow: /dashboard\nDisallow: /enroll\nDisallow: /module/\nDisallow: /payment_callback\n"
    response = make_response(content)
    response.headers['Content-Type'] = 'text/plain'
    return response

@app.route('/<path:undefined_path>')
def catch_all(undefined_path):
    if any(p in undefined_path.lower() for p in ['.php', '.asp', 'wp-', 'admin', '.env', 'config', 'passwd']):
        log_security_event('suspicious_path', details=undefined_path)
    abort(404)

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
