from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import os
import json

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

class QuestionnaireResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    experience_level = db.Column(db.String(50))
    interests = db.Column(db.Text)  # JSON string
    goals = db.Column(db.Text)
    current_skills = db.Column(db.Text)  # JSON string
    learning_style = db.Column(db.String(100))
    time_commitment = db.Column(db.String(50))
    recommended_course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    match_percentage = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    
    recommended_course = db.relationship('Course', backref='questionnaire_responses', lazy=True)

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

# Questionnaire Questions Structure
QUESTIONNAIRE_QUESTIONS = [
    # Section 1: Current Experience
    {
        "id": "q1",
        "section": "experience",
        "question": "What is your current level of tech experience?",
        "type": "single",
        "options": [
            {"value": "absolute_beginner", "label": "Complete beginner - No coding experience", "cyber": 0, "data": 0, "web": 0},
            {"value": "some_basics", "label": "Know some basics - HTML, Excel, basic computer skills", "cyber": 1, "data": 2, "web": 3},
            {"value": "intermediate", "label": "Intermediate - Can write simple programs", "cyber": 2, "data": 3, "web": 3},
            {"value": "advanced", "label": "Advanced - Professional experience in tech", "cyber": 3, "data": 3, "web": 3}
        ]
    },
    {
        "id": "q2",
        "section": "experience",
        "question": "Have you taken any programming or tech courses before?",
        "type": "single",
        "options": [
            {"value": "never", "label": "Never taken any", "cyber": 0, "data": 0, "web": 0},
            {"value": "online_tutorials", "label": "Online tutorials (YouTube, Udemy, etc.)", "cyber": 1, "data": 1, "web": 1},
            {"value": "bootcamp", "label": "Completed a bootcamp or formal course", "cyber": 2, "data": 2, "web": 2},
            {"value": "degree", "label": "Have a tech-related degree", "cyber": 3, "data": 3, "web": 2}
        ]
    },
    {
        "id": "q3",
        "section": "experience",
        "question": "Which of these tools/technologies have you used? (Select all that apply)",
        "type": "multiple",
        "options": [
            {"value": "excel_data", "label": "Excel/Google Sheets for data analysis", "cyber": 0, "data": 3, "web": 0},
            {"value": "python", "label": "Python", "cyber": 2, "data": 3, "web": 2},
            {"value": "javascript", "label": "JavaScript", "cyber": 1, "data": 1, "web": 3},
            {"value": "databases", "label": "SQL/Databases", "cyber": 1, "data": 3, "web": 2},
            {"value": "security_tools", "label": "Security tools (antivirus, VPNs)", "cyber": 3, "data": 0, "web": 0},
            {"value": "none", "label": "None of these", "cyber": 0, "data": 0, "web": 0}
        ]
    },
    # Section 2: Interests & Motivation
    {
        "id": "q4",
        "section": "interests",
        "question": "What aspect of technology excites you most?",
        "type": "single",
        "options": [
            {"value": "protecting_systems", "label": "Protecting systems and fighting cybercrime", "cyber": 5, "data": 0, "web": 0},
            {"value": "analyzing_data", "label": "Analyzing data and finding patterns", "cyber": 0, "data": 5, "web": 1},
            {"value": "building_apps", "label": "Building websites and mobile apps", "cyber": 0, "data": 1, "web": 5},
            {"value": "ai_ml", "label": "AI and machine learning", "cyber": 2, "data": 4, "web": 2}
        ]
    },
    {
        "id": "q5",
        "section": "interests",
        "question": "Which work environment appeals to you?",
        "type": "single",
        "options": [
            {"value": "security_operations", "label": "Security operations center, monitoring threats", "cyber": 5, "data": 0, "web": 0},
            {"value": "data_analysis", "label": "Working with large datasets and analytics", "cyber": 0, "data": 5, "web": 0},
            {"value": "creative_design", "label": "Creative design and user interfaces", "cyber": 0, "data": 0, "web": 5},
            {"value": "problem_solving", "label": "Solving complex technical problems", "cyber": 3, "data": 3, "web": 3}
        ]
    },
    {
        "id": "q6",
        "section": "interests",
        "question": "What type of problems do you enjoy solving?",
        "type": "single",
        "options": [
            {"value": "security_puzzles", "label": "Security puzzles and vulnerabilities", "cyber": 5, "data": 1, "web": 1},
            {"value": "data_insights", "label": "Finding insights from data", "cyber": 1, "data": 5, "web": 1},
            {"value": "user_experience", "label": "Creating great user experiences", "cyber": 0, "data": 1, "web": 5},
            {"value": "system_architecture", "label": "Designing system architecture", "cyber": 2, "data": 3, "web": 3}
        ]
    },
    {
        "id": "q7",
        "section": "interests",
        "question": "What's your long-term career vision?",
        "type": "single",
        "options": [
            {"value": "security_specialist", "label": "Become a security specialist or ethical hacker", "cyber": 5, "data": 0, "web": 0},
            {"value": "data_scientist", "label": "Data scientist or ML engineer", "cyber": 0, "data": 5, "web": 0},
            {"value": "fullstack_dev", "label": "Full-stack developer or tech lead", "cyber": 0, "data": 1, "web": 5},
            {"value": "tech_entrepreneur", "label": "Start my own tech company", "cyber": 1, "data": 2, "web": 4}
        ]
    },
    # Section 3: Skills & Learning
    {
        "id": "q8",
        "section": "skills",
        "question": "Which skills are you most confident in?",
        "type": "multiple",
        "options": [
            {"value": "networking", "label": "Computer networking basics", "cyber": 3, "data": 1, "web": 1},
            {"value": "programming", "label": "Programming/coding", "cyber": 2, "data": 3, "web": 3},
            {"value": "data_analysis", "label": "Data analysis", "cyber": 1, "data": 3, "web": 1},
            {"value": "web_design", "label": "Web design/HTML/CSS", "cyber": 0, "data": 0, "web": 3},
            {"value": "problem_solving", "label": "Logical problem-solving", "cyber": 2, "data": 3, "web": 2},
            {"value": "none_yet", "label": "Still building these skills", "cyber": 0, "data": 0, "web": 0}
        ]
    },
    {
        "id": "q9",
        "section": "skills",
        "question": "How do you prefer to learn?",
        "type": "single",
        "options": [
            {"value": "hands_on", "label": "Hands-on projects and real-world practice", "cyber": 2, "data": 2, "web": 3},
            {"value": "theory_first", "label": "Understanding theory before practice", "cyber": 3, "data": 3, "web": 1},
            {"value": "video_tutorials", "label": "Video tutorials and visual learning", "cyber": 1, "data": 2, "web": 2},
            {"value": "mixed", "label": "Combination of all approaches", "cyber": 2, "data": 2, "web": 2}
        ]
    },
    {
        "id": "q10",
        "section": "skills",
        "question": "How many hours per week can you commit to learning?",
        "type": "single",
        "options": [
            {"value": "less_5", "label": "Less than 5 hours", "cyber": 0, "data": 0, "web": 0},
            {"value": "5_10", "label": "5-10 hours", "cyber": 1, "data": 1, "web": 1},
            {"value": "10_20", "label": "10-20 hours", "cyber": 2, "data": 2, "web": 2},
            {"value": "20_plus", "label": "20+ hours (full-time)", "cyber": 3, "data": 3, "web": 3}
        ]
    },
    {
        "id": "q11",
        "section": "skills",
        "question": "What's your approach to technical challenges?",
        "type": "single",
        "options": [
            {"value": "detective", "label": "Like a detective - investigate and find vulnerabilities", "cyber": 5, "data": 2, "web": 1},
            {"value": "analyst", "label": "Analyze patterns and optimize solutions", "cyber": 1, "data": 5, "web": 2},
            {"value": "builder", "label": "Build and create solutions from scratch", "cyber": 1, "data": 2, "web": 5},
            {"value": "researcher", "label": "Research best practices and implement them", "cyber": 3, "data": 3, "web": 3}
        ]
    },
    # Section 4: Career Goals
    {
        "id": "q12",
        "section": "goals",
        "question": "What type of role are you targeting?",
        "type": "single",
        "options": [
            {"value": "security_analyst", "label": "Cybersecurity Analyst / Penetration Tester", "cyber": 5, "data": 0, "web": 0},
            {"value": "data_engineer", "label": "Data Engineer / Data Analyst", "cyber": 0, "data": 5, "web": 0},
            {"value": "web_developer", "label": "Web Developer / Software Engineer", "cyber": 0, "data": 1, "web": 5},
            {"value": "ml_engineer", "label": "ML Engineer / AI Specialist", "cyber": 1, "data": 5, "web": 1}
        ]
    },
    {
        "id": "q13",
        "section": "goals",
        "question": "Which industry interests you most?",
        "type": "single",
        "options": [
            {"value": "fintech", "label": "Fintech (Paystack, Flutterwave, banks)", "cyber": 4, "data": 3, "web": 3},
            {"value": "cybersecurity", "label": "Cybersecurity firms", "cyber": 5, "data": 1, "web": 0},
            {"value": "tech_startups", "label": "Tech startups and product companies", "cyber": 2, "data": 3, "web": 5},
            {"value": "ecommerce", "label": "E-commerce and digital platforms", "cyber": 2, "data": 3, "web": 4}
        ]
    },
    {
        "id": "q14",
        "section": "goals",
        "question": "What salary range are you targeting? (Monthly in Naira)",
        "type": "single",
        "options": [
            {"value": "entry", "label": "₦150,000 - ₦300,000 (Entry level)", "cyber": 1, "data": 1, "web": 1},
            {"value": "mid", "label": "₦300,000 - ₦600,000 (Mid-level)", "cyber": 2, "data": 2, "web": 2},
            {"value": "senior", "label": "₦600,000 - ₦1,000,000 (Senior)", "cyber": 3, "data": 3, "web": 3},
            {"value": "lead", "label": "₦1,000,000+ (Lead/Principal)", "cyber": 3, "data": 3, "web": 3}
        ]
    },
    {
        "id": "q15",
        "section": "goals",
        "question": "Where do you prefer to work?",
        "type": "single",
        "options": [
            {"value": "lagos", "label": "Lagos, Nigeria", "cyber": 2, "data": 2, "web": 2},
            {"value": "accra", "label": "Accra, Ghana", "cyber": 1, "data": 1, "web": 2},
            {"value": "remote", "label": "Remote from anywhere", "cyber": 2, "data": 3, "web": 3},
            {"value": "flexible", "label": "Flexible / Open to relocation", "cyber": 2, "data": 2, "web": 2}
        ]
    },
    {
        "id": "q16",
        "section": "goals",
        "question": "What motivates you to upskill now?",
        "type": "single",
        "options": [
            {"value": "career_change", "label": "Career change into tech", "cyber": 2, "data": 2, "web": 2},
            {"value": "job_security", "label": "Job security and better opportunities", "cyber": 3, "data": 2, "web": 2},
            {"value": "passion", "label": "Passion for technology and innovation", "cyber": 2, "data": 2, "web": 3},
            {"value": "entrepreneurship", "label": "Start my own tech business", "cyber": 1, "data": 2, "web": 4}
        ]
    }
]

# Job and Company Database
JOB_DATABASE = {
    "Cybersecurity with AI": {
        "jobs": [
            {
                "title": "Cybersecurity Analyst",
                "description": "Monitor and protect systems from threats, analyze security incidents, implement defense strategies",
                "salary_range": "₦200,000 - ₦600,000/month",
                "skills": ["Network Security", "Threat Analysis", "SIEM Tools", "Incident Response", "AI-powered Detection"]
            },
            {
                "title": "Penetration Tester (Ethical Hacker)",
                "description": "Test systems for vulnerabilities, conduct security audits, recommend security improvements",
                "salary_range": "₦300,000 - ₦800,000/month",
                "skills": ["Penetration Testing", "Vulnerability Assessment", "Security Tools", "Python", "AI Attack Vectors"]
            },
            {
                "title": "Security Operations Center (SOC) Analyst",
                "description": "24/7 monitoring of security events, incident response, threat hunting",
                "salary_range": "₦250,000 - ₦700,000/month",
                "skills": ["Security Monitoring", "Log Analysis", "Threat Intelligence", "Automation", "AI-based Alerts"]
            }
        ],
        "companies": ["Flutterwave", "Paystack", "Interswitch", "MTN", "Access Bank", "GT Bank", "Andela", "MainOne"]
    },
    "Data Engineering for AI": {
        "jobs": [
            {
                "title": "Data Engineer",
                "description": "Build and maintain data pipelines, optimize data infrastructure, enable AI/ML workflows",
                "salary_range": "₦300,000 - ₦900,000/month",
                "skills": ["ETL Pipelines", "SQL", "Python", "Cloud (AWS/Azure)", "Apache Airflow", "Data Modeling"]
            },
            {
                "title": "ML Engineer",
                "description": "Develop machine learning models, deploy AI solutions, optimize model performance",
                "salary_range": "₦400,000 - ₦1,200,000/month",
                "skills": ["Machine Learning", "Python", "TensorFlow", "Model Deployment", "Data Pipelines", "MLOps"]
            },
            {
                "title": "Analytics Engineer",
                "description": "Transform raw data into insights, build dashboards, support data-driven decisions",
                "salary_range": "₦250,000 - ₦700,000/month",
                "skills": ["SQL", "Data Visualization", "Python", "Business Intelligence", "Data Warehousing"]
            }
        ],
        "companies": ["Flutterwave", "Paystack", "Andela", "Kuda Bank", "PiggyVest", "Cowrywise", "54gene", "MAX.ng"]
    },
    "Web App Development with AI": {
        "jobs": [
            {
                "title": "Full-Stack Developer",
                "description": "Build complete web applications, integrate AI features, manage frontend and backend",
                "salary_range": "₦300,000 - ₦900,000/month",
                "skills": ["React", "Node.js", "Python/Django", "APIs", "AI Integration", "Databases"]
            },
            {
                "title": "Frontend Engineer",
                "description": "Create responsive UIs, implement AI-powered features, optimize user experience",
                "salary_range": "₦250,000 - ₦700,000/month",
                "skills": ["React/Vue", "JavaScript", "CSS", "AI APIs", "Mobile-First Design", "Performance Optimization"]
            },
            {
                "title": "Backend Developer",
                "description": "Build APIs and services, integrate AI models, manage databases and infrastructure",
                "salary_range": "₦300,000 - ₦850,000/month",
                "skills": ["Python/Node.js", "APIs", "Databases", "Cloud Services", "AI Model Integration", "Security"]
            }
        ],
        "companies": ["Andela", "Flutterwave", "Paystack", "Kuda Bank", "Jumia", "Bolt", "Moniepoint", "Vendease"]
    }
}

CURRICULUM_DATA = {
    "Cybersecurity with AI": [
        ("Week 1", "Security foundations, threat landscape, CIA triad, auth/identity, network basics"),
        ("Week 2", "OS & network hardening, firewalls, VPN/TLS, secure configs, intro cloud security"),
        ("Week 3", "Threat modeling, OWASP Top 10, CVEs, recon basics"),
        ("Week 4", "Logging & SIEM (Splunk/ELK), detection rules, normalization"),
        ("Week 5", "AI for detection: anomaly detection, ML for phishing/malware on logs"),
        ("Week 6", "Phishing defense: email/web, sandboxing, AI-assisted triage"),
        ("Week 7", "Endpoint security & EDR, response playbooks, containment"),
        ("Week 8", "Cloud security (AWS/Azure): IAM, least privilege, segmentation, secrets"),
        ("Week 9", "Incident response lifecycle, tabletop, runbooks, metrics"),
        ("Week 10", "Offensive basics for defenders: exploit chains, password attacks, pentest tooling (ethical)"),
        ("Week 11", "Compliance & governance: NDPA, GDPR basics, vendor risk, policy writing"),
        ("Week 12", "Capstone: AI-assisted detection + response mini-stack, report & hardening plan"),
    ],
    "Data Engineering for AI": [
        ("Week 1", "DE foundations: batch vs streaming, storage formats, schemas"),
        ("Week 2", "Python for DE, Pandas transforms, SQL basics"),
        ("Week 3", "ETL/ELT, Airflow orchestration, DAG design, retries/alerts"),
        ("Week 4", "Data modeling (star/snowflake), partitioning, Parquet/Avro"),
        ("Week 5", "Warehousing vs lake/lakehouse, querying (DuckDB/BigQuery patterns)"),
        ("Week 6", "Data quality & observability: tests, SLAs, lineage basics"),
        ("Week 7", "APIs & ingestion: REST/CSV/JSON, incremental loads, CDC basics"),
        ("Week 8", "Cloud integration (AWS/Azure): object storage, IAM, cost-aware design"),
        ("Week 9", "Streaming intro: Kafka/Kinesis patterns, lightweight demo"),
        ("Week 10", "ML readiness: feature extraction, leakage avoidance, dataset versioning"),
        ("Week 11", "Governance & compliance: NDPA/GDPR basics, PII handling, access controls"),
        ("Week 12", "Capstone: end-to-end pipeline → clean/validate → model-ready dataset + ML trigger"),
    ],
    "Web App Development with AI": [
        ("Week 1", "Web fundamentals: HTTP/REST/JSON, accessibility, toolchain setup"),
        ("Week 2", "Frontend (React/Vue): components, state/props, routing, forms"),
        ("Week 3", "Styling systems: responsive layouts, design tokens, accessibility passes"),
        ("Week 4", "Backend (Flask/Express): routing, controllers, auth/session/JWT"),
        ("Week 5", "Data layer: SQL vs NoSQL, ORM basics, migrations, CRUD API"),
        ("Week 6", "AI integrations: call LLM API, prompt design, errors/timeouts/retries"),
        ("Week 7", "AI patterns: search+summarize, chatbot, recommendations; guardrails/rate limits"),
        ("Week 8", "Security: OWASP Top 10, secure headers, validation, secrets handling"),
        ("Week 9", "Performance: caching, CDN, lazy loading, bundle optimization, CWV basics"),
        ("Week 10", "Testing: unit/integration/API, component tests, CI basics"),
        ("Week 11", "Deployment: containerize, env configs, deploy (Render/Heroku/Vercel), monitoring"),
        ("Week 12", "Capstone: full-stack AI app (chatbot/FAQ/recommender) with auth, DB, deployment"),
    ],
}

# Recommendation Engine
def calculate_course_recommendation(responses):
    """Calculate which course best matches user responses"""
    scores = {
        'Cybersecurity with AI': 0,
        'Data Engineering for AI': 0,
        'Web App Development with AI': 0
    }
    
    for question_id, answer in responses.items():
        question = next((q for q in QUESTIONNAIRE_QUESTIONS if q['id'] == question_id), None)
        if not question:
            continue
            
        if question['type'] == 'single':
            # Single choice question
            option = next((opt for opt in question['options'] if opt['value'] == answer), None)
            if option:
                scores['Cybersecurity with AI'] += option.get('cyber', 0)
                scores['Data Engineering for AI'] += option.get('data', 0)
                scores['Web App Development with AI'] += option.get('web', 0)
        elif question['type'] == 'multiple':
            # Multiple choice question
            if isinstance(answer, list):
                for ans_value in answer:
                    option = next((opt for opt in question['options'] if opt['value'] == ans_value), None)
                    if option:
                        scores['Cybersecurity with AI'] += option.get('cyber', 0)
                        scores['Data Engineering for AI'] += option.get('data', 0)
                        scores['Web App Development with AI'] += option.get('web', 0)
    
    # Find the course with highest score
    max_score = max(scores.values())
    if max_score == 0:
        # Default to web development if no clear match
        recommended_course = 'Web App Development with AI'
        match_percentage = 60
    else:
        recommended_course = max(scores, key=scores.get)
        # Calculate match percentage (normalize to 0-100)
        total_possible = len(QUESTIONNAIRE_QUESTIONS) * 5  # Max score per question is 5
        match_percentage = min(int((max_score / total_possible) * 100), 99)
    
    return recommended_course, match_percentage, scores

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
    curriculum = CURRICULUM_DATA.get(course.title, [])
    return render_template('course_detail.html', course=course, curriculum=curriculum)

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

@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html', questions=QUESTIONNAIRE_QUESTIONS)

@app.route('/questionnaire/submit', methods=['POST'])
def questionnaire_submit():
    # Get form responses
    responses = {}
    for question in QUESTIONNAIRE_QUESTIONS:
        q_id = question['id']
        if question['type'] == 'multiple':
            # Get all selected values for checkbox questions
            responses[q_id] = request.form.getlist(q_id)
        else:
            # Get single value for radio questions
            responses[q_id] = request.form.get(q_id)
    
    # Calculate recommendation
    recommended_course_name, match_percentage, all_scores = calculate_course_recommendation(responses)
    
    # Get the course from database
    recommended_course = Course.query.filter_by(title=recommended_course_name).first()
    
    # Generate unique session ID
    import uuid
    session_id = str(uuid.uuid4())
    
    # Store in database (anonymous)
    questionnaire_response = QuestionnaireResponse(
        session_id=session_id,
        experience_level=responses.get('q1', ''),
        interests=json.dumps(responses.get('q4', '')),
        goals=json.dumps(responses.get('q12', '')),
        current_skills=json.dumps(responses.get('q8', [])),
        learning_style=responses.get('q9', ''),
        time_commitment=responses.get('q10', ''),
        recommended_course_id=recommended_course.id if recommended_course else None,
        match_percentage=match_percentage,
        ip_address=request.remote_addr
    )
    db.session.add(questionnaire_response)
    db.session.commit()
    
    # Redirect to results page
    return redirect(url_for('questionnaire_results', session_id=session_id))

@app.route('/results/<session_id>')
def questionnaire_results(session_id):
    # Get questionnaire response
    response = QuestionnaireResponse.query.filter_by(session_id=session_id).first_or_404()
    
    # Get recommended course
    course = response.recommended_course
    
    # Get job data for this course
    job_data = JOB_DATABASE.get(course.title, {})
    
    return render_template('questionnaire_results.html',
                         course=course,
                         match_percentage=response.match_percentage,
                         jobs=job_data.get('jobs', []),
                         companies=job_data.get('companies', []))

if __name__ == '__main__':
    app.run(debug=True)

