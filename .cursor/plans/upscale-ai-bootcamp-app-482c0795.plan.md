<!-- 482c0795-f88c-49b6-b396-3f6b7f760e37 46df5587-35df-4b6f-8ba1-0b8315b9d472 -->
# Upscale AI Bootcamp Web Application

## Overview

Build a full-featured Flask web app for the Upscale AI Bootcamp, targeting West African users with courses in Cybersecurity, Data Engineering, and Web Development.

## Core Components

### 1. Application Setup

- Create `app.py` with Flask, SQLAlchemy, and Flask-Login configuration
- Set up SQLite database (`upscale.db`) with models for:
  - **User**: authentication, payment plan tracking
  - **Payment**: Paystack transaction records
  - **Course**: bootcamp courses
  - **Module**: course content modules
  - **Progress**: user progress tracking per module
- Seed database with 3 courses (Cybersecurity, Data Engineering, Web Dev) and sample modules

### 2. User Authentication System

- Registration page with name, email, password (hashed with werkzeug)
- Login/logout functionality using Flask-Login
- Protected routes requiring authentication
- Session management

### 3. Payment Integration (Paystack)

- Enrollment page with payment options:
  - Full payment: ₦150,000 (discounted)
  - Monthly installments: ₦50,000 × 3 months
- Initialize Paystack transactions via API
- Payment callback verification
- Store payment status in database

### 4. Course & Module System

- Course listing on home page
- Dashboard showing enrolled courses
- Module pages with content display
- Mark modules as complete functionality
- Progress tracking per user per module

### 5. AI Personalization (Rule-Based)

- `recommend_module()` function using simple logic
- Recommends next incomplete module based on user progress
- Displayed on dashboard for each course
- Extensible for future scikit-learn integration

### 6. UI/UX with Bootstrap

- Create `base.html` template with Bootstrap 5 CDN
- Responsive navbar with authentication state
- Flash messages for user feedback
- Mobile-responsive design for West African users
- Templates: index, register, login, enroll, dashboard, module

## File Structure

```
/Users/ndmx0/DEV/Upscale/
├── app.py
├── upscale.db (generated on first run)
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── enroll.html
│   ├── dashboard.html
│   └── module.html
└── requirements.txt (optional)
```

## Dependencies

- flask
- flask-sqlalchemy
- flask-login
- requests (for Paystack API)

## Configuration Required

- Update `SECRET_KEY` in app.py (for production)
- Add Paystack secret key from dashboard (test/live mode)

## Testing Steps

1. Install dependencies: `pip install flask flask-sqlalchemy flask-login requests`
2. Run app: `python app.py`
3. Register new user at http://127.0.0.1:5000/register
4. Enroll with payment option (redirects to Paystack)
5. View dashboard with courses, moduxles, progress, and recommendations
6. Complete modules and track progress

### To-dos

- [x] Create app.py with Flask configuration, database models, and seed data
- [x] Create templates directory structure
- [x] Create base.html with Bootstrap 5 and navigation
- [x] Create register.html and login.html templates
- [x] Create index.html, enroll.html, dashboard.html, and module.html templates
- [x] Verify app runs, database initializes, and all routes are accessible