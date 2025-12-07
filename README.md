# Upskill Institute Web Application

Flask-powered platform for Upskill Institute, serving AI-infused courses for ambitious professionals.

## What’s Inside
- Secure auth (login, registration) with CSRF protection and rate limiting
- Course browsing, module tracking, and career questionnaire with recommendations
- Paystack payments (Naira) with cohort-focused enrollment flows
- Responsive UI tailored for mobile-first usage

## Quick Start
1) Clone and install:
```bash
git clone https://github.com/ndmx/upscale.git
cd upscale
pip install -r requirements.txt
```
2) Create a `.env` (not committed) with:
```
SECRET_KEY=<secure-random>
DATABASE_URL=<postgres-connection-string>
PAYSTACK_SECRET_KEY=<paystack-secret>
FLASK_ENV=development
```
3) Run locally:
```bash
python app.py
```
Visit `http://127.0.0.1:5000/`.

## Notes
- Deployment guides and sample env files are kept local only.
- For support: support@upskillsinstitute.org
