# Upskill Institute Web Application

A Flask-based web application for Upskill Institute, democratizing AI-adapted skills in cybersecurity, data engineering, and web development for West African professionals.

**Live Site:** [upskillsinstitute.org](https://upskillsinstitute.org)

## Features

- **User Authentication**: Secure registration and login system with password hashing
- **Payment Integration**: Paystack integration for Nigerian Naira transactions
  - Full payment option: ₦150,000 (discounted)
  - Monthly installments: ₦50,000 × 3 months
- **Course Management**: 3 courses with multiple modules each
  - Cybersecurity with AI
  - Data Engineering for AI
  - Web App Development with AI
- **Progress Tracking**: Track module completion for each user
- **AI Personalization**: Rule-based recommendation system for next modules
- **Career Questionnaire**: 16-question assessment with personalized course recommendations
- **Security Features**: CSRF protection, rate limiting, secure headers
- **Responsive UI**: Apple-inspired design, mobile-responsive

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning the repository)

## Quick Start - Run the App Locally

### 🍎 macOS / 🐧 Linux

1. **Clone the repository**:
```bash
git clone https://github.com/YOUR_USERNAME/upskillsinstitute.git
cd upskillsinstitute
```

2. **Run the automated setup script**:
```bash
chmod +x setup.sh
./setup.sh
```

3. **Start the application**:
```bash
python3 app.py
```

4. **View in browser**:
   - Open: `http://127.0.0.1:5000/`

### 🪟 Windows

1. **Clone the repository**:
```cmd
git clone https://github.com/YOUR_USERNAME/upskillsinstitute.git
cd upskillsinstitute
```

2. **Install dependencies**:
```cmd
pip install -r requirements.txt
```

3. **Start the application**:
```cmd
python app.py
```

4. **View in browser**:
   - Open: `http://127.0.0.1:5000/`

## Environment Variables

For production, set these environment variables:

```bash
SECRET_KEY=your-secure-random-key
DATABASE_URL=postgresql://user:password@host:5432/upskill
PAYSTACK_SECRET_KEY=sk_live_your_key
FLASK_ENV=production
```

## Project Structure

```
upskillsinstitute/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── Procfile                  # Production server configuration
├── runtime.txt               # Python version for hosting
├── setup.sh                  # Automated setup script
├── DEPLOYMENT.md             # Deployment guide
├── static/
│   ├── css/
│   │   └── custom.css       # Apple-inspired styling
│   └── icons/               # Favicon files
├── templates/               # HTML templates
│   ├── base.html            # Base template
│   ├── index.html           # Home page
│   ├── courses.html         # Course listing
│   ├── course_detail.html   # Individual course pages
│   ├── questionnaire.html   # Career assessment
│   ├── questionnaire_results.html
│   ├── register.html        # Registration
│   ├── login.html           # Login
│   ├── enroll.html          # Enrollment/payment
│   ├── dashboard.html       # User dashboard
│   ├── module.html          # Module view
│   └── errors/              # Custom error pages
│       ├── 400.html
│       ├── 403.html
│       ├── 404.html
│       ├── 413.html
│       ├── 429.html
│       └── 500.html
├── logs/                    # Application logs
└── instance/
    └── upskill.db          # SQLite database (development)
```

## Database Models

- **User**: User accounts with authentication and account lockout
- **Payment**: Payment transaction records
- **Course**: Course information
- **Module**: Course content modules
- **Progress**: User progress per module
- **QuestionnaireResponse**: Career assessment responses
- **SecurityLog**: Security event logging

## Security Features

- CSRF protection on all forms
- Rate limiting (50 requests/hour)
- Secure password hashing (PBKDF2-SHA256)
- Account lockout after 5 failed attempts
- Security headers (XSS, Clickjacking, etc.)
- Input validation and sanitization
- Suspicious path detection

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production deployment instructions.

Recommended platform: **Render** ($7/month for always-on)

## Support

For issues or questions, contact: support@upskillsinstitute.org

## License

Proprietary - Upskill Institute

---

**Built for West African Professionals** 🌍
