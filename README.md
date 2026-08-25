# Seva Bandhu

Seva Bandhu is a Django-based local-service coordination application. It supports separate customer and technician flows for account access, service requests, job tracking, service management, payments, invoices, and real-time location/status updates.

## Technology

- Backend: Python, Django, Django Channels
- Frontend: Django templates (the `SevaBandhu-Frontend/` directory is reserved for a future standalone UI)
- Database: SQLite for local development; a `DATABASE_URL` can be supplied for deployment

## Project structure

```text
SevaBandhu/
├── backend/                 # Django project, app, migrations, and local media
├── SevaBandhu-Frontend/     # Reserved for a future standalone frontend
├── .env.example             # Safe environment-variable template
├── .gitignore
└── README.md
```

## Local setup

1. Create and activate a virtual environment.
2. Install backend dependencies:

   ```powershell
   cd backend
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` in the repository root, then load its variables in your shell or deployment environment. Set `DJANGO_SECRET_KEY`.
4. Run migrations if creating a new local database:

   ```powershell
   python manage.py migrate
   ```

5. Start the backend:

   ```powershell
   python manage.py runserver 8001
   ```

The existing interface is served by Django templates. `SevaBandhu-Frontend/` has no standalone application yet; add its own `package.json` and setup instructions there only when that frontend is created.

### Email verification

For real verification emails, set these values in the ignored root `.env` file using your SMTP provider's credentials:

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=your-smtp-host
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-smtp-username
EMAIL_HOST_PASSWORD=your-smtp-password-or-app-password
DEFAULT_FROM_EMAIL=your-verified-sender-address
PUBLIC_BASE_URL=https://your-public-domain.example
```

Use either TLS or SSL, not both. With no SMTP host configured, development mode safely shows a local verification link instead of sending a real email.

## Security notes

- Never commit `.env`, `backend/db.sqlite3`, or `backend/media/`.
- Use a unique Django secret for each environment.
- Rotate any credential that was committed or shared before this cleanup.
- Create administrators explicitly with `python manage.py createsuperuser`; the application does not create default accounts at startup.

## Future improvements

- Add a standalone frontend when the Django-template UI is intentionally replaced.
- Add automated tests and deployment-specific environment configuration.
