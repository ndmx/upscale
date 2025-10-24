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

## Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install flask flask-sqlalchemy flask-login requests
```

2. **Configure Paystack**:
   - Sign up at [Paystack](https://paystack.com/)
   - Get your Secret Key from the dashboard
   - Open `app.py` and replace `'your_paystack_secret_key'` with your actual key
   - For testing, use test mode keys (starts with `sk_test_`)

3. **Update Secret Key**:
   - In `app.py`, change `'your_secret_key_change_this'` to a random string for production

## Running the Application

1. **Start the Flask server**:
```bash
python app.py
```

2. **Access the application**:
   - Open your browser and navigate to: `http://127.0.0.1:5000/`
   - The database (`upscale.db`) will be created automatically on first run

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
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── upscale.db            # SQLite database (auto-generated)
├── templates/            # HTML templates
│   ├── base.html         # Base template with Bootstrap
│   ├── index.html        # Home page
│   ├── register.html     # Registration form
│   ├── login.html        # Login form
│   ├── enroll.html       # Enrollment/payment form
│   ├── dashboard.html    # User dashboard
│   └── module.html       # Individual module view
└── README.md             # This file
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

