# Parua Local Football League - Simple Live Score System

## Setup
1. Install Python.
2. Open this folder in VS Code.
3. Create/activate a virtual environment.
4. Run:
   pip install -r requirements.txt
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver

## Use
Open http://127.0.0.1:8000/
Admin panel: http://127.0.0.1:8000/admin/

Create teams first, then create matches.
Set a match to `live` to show it in the LIVE section.
Set `clock_running` to true and enter `clock_seconds` to start the visible browser clock.
Add goals/cards/substitutions through Match Events.
Set status to `finished` after the match.

## Railway deployment
1. Push this project to GitHub and create a new Railway project from the repository.
2. Add a PostgreSQL service in Railway. Railway provides its `DATABASE_URL` automatically.
3. Add these Railway variables:
   - `SECRET_KEY`: a long random production secret
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: your Railway hostname, for example `your-app.up.railway.app`
   - `CSRF_TRUSTED_ORIGINS`: your full Railway URL, for example `https://your-app.up.railway.app`
4. Add a Railway Volume mounted at `/app/media` so team logos survive redeployments.
5. Deploy. Railway uses the included `Procfile` or `railway.json` to migrate, collect static files, and start Gunicorn.

Railway can provide `RAILWAY_PUBLIC_DOMAIN` automatically. The Django settings use it to trust the HTTPS public URL. If it is not available in your service variables, set `RAILWAY_PUBLIC_DOMAIN=livescore.up.railway.app` or set `CSRF_TRUSTED_ORIGINS=https://livescore.up.railway.app`.

The included configuration keeps SQLite for local development and automatically uses Railway PostgreSQL when `DATABASE_URL` is present. Do not commit `.env` or production secrets.
