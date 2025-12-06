# Upscale AI Bootcamp Web Application

A Flask-based web application for the Upscale AI Bootcamp, democratizing AI-adapted skills in cybersecurity, data engineering, and web development for West African users.

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
- **Responsive UI**: Bootstrap 5 mobile-responsive design

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning the repository)

## Quick Start - Run the App Locally

Choose your operating system and follow the instructions below:

### 🍎 macOS / 🐧 Linux

1. **Clone the repository**:
```bash
git clone https://github.com/ndmx/upscale.git
cd upscale
```

2. **Run the automated setup script**:
```bash
chmod +x setup.sh
./setup.sh
```

3. **Configure your keys** (after setup completes):
   - Open `app.py` in your text editor
   - Line 9: Replace `'your_secret_key_change_this'` with a secure random string
   - Line 12: Add your Paystack secret key (get it from [Paystack Dashboard](https://dashboard.paystack.com/#/settings/developer))
   - For testing, use test mode keys (starts with `sk_test_`)

4. **Start the application**:
```bash
python3 app.py
```

5. **View in browser**:
   - Open: `http://127.0.0.1:5000/`
   - The app is now running on your local device! 🚀

### 🪟 Windows

1. **Clone the repository**:
```cmd
git clone https://github.com/ndmx/upscale.git
cd upscale
```

2. **Install dependencies manually** (Windows doesn't support .sh scripts):
```cmd
pip install -r requirements.txt
```

Or install packages individually:
```cmd
pip install flask flask-sqlalchemy flask-login requests
```

3. **Configure your keys**:
   - Open `app.py` in Notepad or your preferred editor
   - Line 9: Replace `'your_secret_key_change_this'` with a secure random string
   - Line 12: Add your Paystack secret key (get it from [Paystack Dashboard](https://dashboard.paystack.com/#/settings/developer))
   - For testing, use test mode keys (starts with `sk_test_`)

4. **Start the application**:
```cmd
python app.py
```

5. **View in browser**:
   - Open: `http://127.0.0.1:5000/`
   - The app is now running on your local device! 🚀

## Alternative Manual Installation (All Platforms)

If the automated setup doesn't work, follow these steps:

1. **Verify Python installation**:
```bash
python3 --version  # macOS/Linux
python --version   # Windows
```
Should show Python 3.8 or higher.

2. **Install dependencies**:
```bash
pip3 install flask flask-sqlalchemy flask-login requests  # macOS/Linux
pip install flask flask-sqlalchemy flask-login requests   # Windows
```

3. **Configure secrets** (see configuration steps above)

4. **Run the app**:
```bash
python3 app.py  # macOS/Linux
python app.py   # Windows
```

5. **Access in browser**: Navigate to `http://127.0.0.1:5000/`

## First Run Notes

- The database (`upscale.db`) will be created automatically on first run
- Sample courses with modules will be seeded automatically
- No internet connection needed after dependencies are installed (except for Paystack payments)

## Usage Flow

1. **Register**: Click "Get Started" or "Register" to create an account
2. **Enroll**: After registration, choose a payment plan
3. **Payment**: Complete payment through Paystack (redirects to payment page)
4. **Dashboard**: Access courses and modules after successful payment
5. **Learn**: Complete modules and track your progress
6. **AI Recommendations**: Get personalized module recommendations based on your progress

## Project Structure

```
Upscale/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── setup.sh                  # Automated setup script (macOS/Linux)
├── instance/
│   └── upscale.db           # SQLite database (auto-generated)
├── static/
│   └── css/
│       └── custom.css       # Custom styling
├── templates/               # HTML templates
│   ├── base.html            # Base template with Bootstrap
│   ├── index.html           # Home page
│   ├── courses.html         # Public course listing
│   ├── course_detail.html   # Individual course pages
│   ├── register.html        # Registration form
│   ├── login.html           # Login form
│   ├── enroll.html          # Enrollment/payment form
│   ├── dashboard.html       # User dashboard
│   └── module.html          # Individual module view
└── README.md                # This file
```

## Database Models

- **User**: User accounts with authentication
- **Payment**: Payment transaction records
- **Course**: Course information
- **Module**: Course content modules
- **Progress**: User progress per module

## Future Enhancements

- Add scikit-learn for advanced AI personalization
- Implement quiz system with adaptive difficulty
- Add video content support
- Email notifications for course updates
- Admin dashboard for content management
- Certificate generation upon course completion

## Deployment

For production deployment, consider:
- Using PostgreSQL instead of SQLite
- Setting up a production WSGI server (gunicorn, uwsgi)
- Configuring environment variables for secrets
- Using HTTPS
- Deploying to platforms like Heroku, AWS, or DigitalOcean

## Support

For issues or questions, contact the Upscale team.

## License

Proprietary - Upscale AI Bootcamp

---

**Designed by edentv** - Creator Studio
