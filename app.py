from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_change_this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///upscale.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PAYSTACK_SECRET_KEY'] = 'your_paystack_secret_key'  # From Paystack dashboard
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    payment_plan = db.Column(db.String(50))
    payments = db.relationship('Payment', backref='user', lazy=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), unique=True)
    amount = db.Column(db.Integer)  # In kobo
    status = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)  # Changed to Text for longer descriptions
    modules = db.relationship('Module', backref='course', lazy=True)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    progresses = db.relationship('Progress', backref='module', lazy=True)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'))
    completed = db.Column(db.Boolean, default=False)

# Load user for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create DB and seed data if not exists
with app.app_context():
    db.create_all()
    if Course.query.count() == 0:
        courses_data = [
            {"title": "Cybersecurity with AI", "description": "Master the fusion of traditional cybersecurity practices with cutting-edge AI to combat evolving digital threats in West Africa. This course equips you with skills to detect AI-powered attacks, build intelligent defense systems, and ensure secure digital ecosystems amid rising cybercrimes in regions like Nigeria and Ghana.", "modules": [
                {"title": "Intro to AI Threats", "content": "Explore how AI is weaponized in cyber attacks, including deepfakes and automated phishing tailored to West African mobile banking vulnerabilities. Learn to identify risks in real-world scenarios like fintech scams and social engineering."},
                {"title": "Defensive AI Tools", "content": "Hands-on training with machine learning models for anomaly detection and threat prediction. Build AI-driven firewalls and intrusion systems using Python libraries, adapted for low-bandwidth environments common in Senegal and Cameroon."},
                {"title": "Ethical AI in Security", "content": "Delve into AI biases in cybersecurity tools and ethical considerations for deployment in diverse West African contexts. Case studies on protecting critical infrastructure like power grids from AI-enhanced ransomware."}
            ]},
            {"title": "Data Engineering for AI", "description": "Learn to engineer robust data pipelines optimized for AI applications, addressing West Africa's unique challenges like intermittent connectivity and diverse data sources. This course adapts core data skills to power AI models for scalable, efficient solutions in industries from agriculture to healthcare.", "modules": [
                {"title": "ETL Basics for AI", "content": "Design extract, transform, load processes with AI automation, handling unstructured data from regional sources like mobile transactions in Benin. Use tools like Pandas and Apache Airflow for resilient pipelines."},
                {"title": "Cloud Integration and Scalability", "content": "Integrate cloud platforms like AWS or Azure with AI data needs, focusing on cost-effective scaling for West African startups. Practical projects on building data lakes for AI training amid power outages."},
                {"title": "Data Governance with AI", "content": "Implement AI-assisted data quality checks and compliance with laws like Nigeria's NDPA. Explore real-time processing for AI applications in e-commerce and public sector data management."}
            ]},
            {"title": "Web App Development with AI", "description": "Adapt web development fundamentals to incorporate AI for smarter, interactive applications suited to West African users. From mobile-first designs to AI-enhanced features, this course prepares you to build secure, accessible apps that solve local problems like e-learning platforms and fintech tools.", "modules": [
                {"title": "React with AI APIs", "content": "Build full-stack web apps using React and integrate AI APIs like those from OpenAI for features such as chatbots. Focus on responsive designs for high smartphone usage in Ghana and Senegal."},
                {"title": "Deployment and Security", "content": "Deploy AI-integrated apps on platforms like Vercel or Heroku, with emphasis on security against regional threats. Hands-on with CI/CD pipelines and performance optimization for low-latency access."},
                {"title": "AI-Enhanced User Experiences", "content": "Create personalized web features using AI, such as recommendation engines for e-commerce. Address accessibility for diverse users, including offline capabilities for rural West Africa."}
            ]}
        ]
        for c in courses_data:
            course = Course(title=c["title"], description=c["description"])
            db.session.add(course)
            db.session.commit()
            for m in c["modules"]:
                module = Module(title=m["title"], content=m["content"], course_id=course.id)
                db.session.add(module)
            db.session.commit()

# Simple AI recommendation (rule-based; expand with scikit-learn later)
def recommend_module(user_id, course_id):
    completed = Progress.query.filter_by(user_id=user_id, completed=True).count()
    modules = Module.query.filter_by(course_id=course_id).order_by(Module.id).all()
    if completed < len(modules):
        return modules[completed]  # Next incomplete module
    return None

@app.route('/')
def home():
    courses = Course.query.all()
    return render_template('index.html', courses=courses)

@app.route('/courses')
def courses():
    all_courses = Course.query.all()
    return render_template('courses.html', courses=all_courses)

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course_detail.html', course=course)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))
        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('enroll'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/enroll', methods=['GET', 'POST'])
@login_required
def enroll():
    if request.method == 'POST':
        payment_plan = request.form['payment']
        amount = 15000000 if payment_plan == 'full' else 5000000  # In kobo; e.g., ₦150,000 full or ₦50,000/month
        current_user.payment_plan = payment_plan
        db.session.commit()

        # Initialize Paystack transaction
        headers = {'Authorization': f'Bearer {app.config["PAYSTACK_SECRET_KEY"]}', 'Content-Type': 'application/json'}
        data = {
            'email': current_user.email,
            'amount': amount,
            'reference': f'upscale_{current_user.id}_{os.urandom(8).hex()}',  # Unique ref
            'callback_url': url_for('payment_callback', _external=True)
        }
        response = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=data)
        if response.status_code == 200:
            resp_data = response.json()
            if resp_data['status']:
                payment = Payment(reference=resp_data['data']['reference'], amount=amount, status='pending', user_id=current_user.id)
                db.session.add(payment)
                db.session.commit()
                return redirect(resp_data['data']['authorization_url'])
        flash('Payment initialization failed.')
    return render_template('enroll.html')

@app.route('/payment_callback')
@login_required
def payment_callback():
    reference = request.args.get('reference')
    if not reference:
        flash('No reference provided.')
        return redirect(url_for('dashboard'))

    # Verify transaction
    headers = {'Authorization': f'Bearer {app.config["PAYSTACK_SECRET_KEY"]}'}
    response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    if response.status_code == 200:
        resp_data = response.json()
        if resp_data['status'] and resp_data['data']['status'] == 'success':
            payment = Payment.query.filter_by(reference=reference).first()
            if payment:
                payment.status = 'success'
                db.session.commit()
                flash('Payment successful! Access your courses.')
                return redirect(url_for('dashboard'))
    flash('Payment verification failed.')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    courses = Course.query.all()
    progresses = {p.module_id: p.completed for p in Progress.query.filter_by(user_id=current_user.id).all()}
    recommendations = {}
    for course in courses:
        rec = recommend_module(current_user.id, course.id)
        if rec:
            recommendations[course.id] = rec.title
    return render_template('dashboard.html', courses=courses, progresses=progresses, recommendations=recommendations, user=current_user)

@app.route('/module/<int:module_id>', methods=['GET', 'POST'])
@login_required
def view_module(module_id):
    module = Module.query.get_or_404(module_id)
    progress = Progress.query.filter_by(user_id=current_user.id, module_id=module_id).first()
    if request.method == 'POST':
        if not progress:
            progress = Progress(user_id=current_user.id, module_id=module_id, completed=True)
            db.session.add(progress)
        else:
            progress.completed = True
        db.session.commit()
        flash('Module completed!')
        return redirect(url_for('dashboard'))
    return render_template('module.html', module=module, completed=progress.completed if progress else False)

if __name__ == '__main__':
    app.run(debug=True)

