# MSA AcadBot — Backend

Backend API for the More Success Academy AcadBot platform. Built with Django REST Framework, session authentication, and PostgreSQL.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 5.x, Django REST Framework 3.x |
| Auth | Session + CSRF (cookie-based) |
| Database | PostgreSQL (production), SQLite (development) |
| Caching | Local memory (LocMemCache) |
| API Schema | DRF Spectacular (OpenAPI 3) |
| Error Tracking | Sentry (privacy-compliant, `send_default_pii=False`) |
| Static Files | WhiteNoise (production) |
| Task Queue | Celery + Redis (optional) |

---

## Project Structure

```
acadbot_demo/
├── apps/
│   ├── accounts/        # User management, profiles, roles
│   ├── careers/         # Career paths, skills, roadmaps, interview questions
│   ├── courses/         # Courses, lessons, enrollment, progress
│   ├── matching/        # Student-mentor matching requests and suggestions
│   ├── sessions/        # Session scheduling, availability, feedback
│   ├── progress/        # Skill assessments, milestones, learning paths, snapshots
│   ├── dashboard/       # Analytics for students, mentors, admins
│   └── core/            # Shared permissions, exceptions, utilities
├── config/
│   ├── settings/
│   │   ├── base.py      # Shared configuration
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py          # Root URL routing
│   └── wsgi.py / asgi.py
├── manage.py
└── requirements/
```

---

## API Endpoints

All endpoints live under `/api/`:

| App | Base Path | Key Resources |
|-----|-----------|---------------|
| Authentication | `/auth/` | register, login, logout, me, profiles |
| Careers | `/careers/` | careers, skills, roadmap stages, interview questions |
| Courses | `/courses/` | courses, enrollments, lessons, quizzes |
| Matching | `/matching/` | match requests, matches, mentor suggestions |
| Sessions | `/sessions/` | sessions, recurrences, availability, feedback |
| Progress | `/progress/` | assessments, milestones, learning paths, snapshots |
| Dashboard | `/dashboard/` | student, mentor, admin overviews |

Interactive docs: `/api/docs/` (Swagger UI), `/api/redoc/` (ReDoc), `/api/schema/` (OpenAPI JSON).

---

## Authentication Flow

1. `GET /api/auth/csrf/` — get CSRF token
2. `POST /api/auth/register/` — create account (student or mentor)
3. `POST /api/auth/login/` — sets session cookie
4. Subsequent requests: include session cookie + `X-CSRFToken` header

All endpoints require authentication except public career/mentor listings.

---

## Permissions

| Class | Purpose |
|-------|---------|
| `AllowAny` | Public endpoints (careers, mentor listings, auth) |
| `IsAuthenticated` | Default for all other endpoints |
| `IsStudent` | Student-only: enrollments, lessons, match requests, progress |
| `IsMentor` | Mentor-only: availability, accept/decline matches, start sessions |
| `IsOwnerOrReadOnly` | Profile updates (owner only) |
| `IsOwnerOrMentorOrAdmin` | Sessions, matches, recurrences |
| `IsAdmin` | Admin dashboard endpoints |

---

## Configuration

Environment variables (managed via `python-decouple`):

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | required |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `''` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL | required (prod) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins | `''` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins | `''` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP | required (prod) |
| `SENTRY_DSN` | Sentry DSN | optional |
| `REDIS_URL` | Redis connection | optional |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery | optional |

Development uses `.env` (git-ignored). Production sets variables in the platform dashboard.

---

## Database

Migrations are version-controlled. Apply with:

```bash
python manage.py migrate
```

Models cover:
- Users (custom model with student/mentor roles)
- Student/Mentor profiles
- Careers, skills, roadmap stages, interview questions
- Courses, lessons, enrollments, lesson progress
- Match requests, matches, mentor suggestions
- Sessions, recurrences, availability, feedback
- Skill assessments, milestones, learning paths, progress snapshots

---

## Running Locally

```bash
# Clone
git clone https://github.com/KehindeALX/acadbot_demo.git
cd acadbot_demo

# Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencies
pip install -r requirements/base.txt

# Environment
cp .env.example .env  # edit values if needed

# Database
python manage.py migrate

# Run
python manage.py runserver
```

Server starts at `http://localhost:8000/`. API at `http://localhost:8000/api/`.

---

## Production Deployment

Key production settings in `config/settings/production.py`:

- `DEBUG = False`
- PostgreSQL with SSL (`sslmode=require`)
- Secure headers (HSTS, CSP, referrer policy, etc.)
- WhiteNoise for static files
- Database-backed sessions
- LocMemCache (swap for Redis when available)
- Sentry with `send_default_pii=False`
- Strict CORS/CSRF from environment variables

Deploy checklist:
1. Set all required environment variables
2. Run `python manage.py collectstatic`
3. Run migrations
4. Ensure `ALLOWED_HOSTS` and CORS/CSRF origins match your domain
5. Configure reverse proxy (nginx) + gunicorn/uvicorn

---

## Code Quality

- Custom exception handler (`apps.core.exceptions.custom_exception_handler`)
- Consistent response envelope: `{ "success": true, "data": ..., "message": "..." }`
- Error envelope: `{ "success": false, "error": { "code": 400, "message": "...", "details": {} } }`
- Page-number pagination (default 20)
- Filtering via `django-filter`, search, ordering
- Select/prefetch related in all viewsets for N+1 prevention

---

## Testing

```bash
# Run tests
python manage.py test

# Check for missing migrations
python manage.py makemigrations --check --dry-run
```

---

## Branching Strategy

- `main` — production-ready
- `william` — active development branch
- Feature branches off `william`, PR back to `william`
- Merge `william` → `main` for releases

---

## Recent Changes (Branch: william)

| Commit | Description |
|--------|-------------|
| `cb50b8e` | Add comprehensive API documentation |
| `2e7a465` | Revert workaround commit 9a1266c; restore DRF Spectacular, Debug Toolbar, PostgreSQL |
| `e53cf09` | Fix `IsOwnerOrMentorOrAdmin` permission logic; production hardening (LocMemCache, DB sessions, Sentry `send_default_pii=False`) |
| `e003068` | Remove stray file `=5.0,` |

---

## License

Internal project — More Success Academy.