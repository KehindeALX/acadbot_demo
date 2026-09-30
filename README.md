# MSA AcadBot

The More Success Academy AcadBot platform: a Django REST Framework backend and the static frontend that consumes it. Session authentication, PostgreSQL, Paystack subscriptions and generated certificates.

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
| PDF Generation | reportlab (certificates, generated in memory) |
| AI Guide | OpenRouter chat completions (the "Abia" career guide) |
| Payments | Paystack (subscriptions, webhook verified) |
| Content Authoring | OpenRouter, via the `draft_course` management command |
| Tests | pytest + pytest-django |
| Task Queue | Celery + Redis (optional) |

---

## Project Structure

```
acadbot_demo/
├── apps/
│   ├── accounts/        # User management, profiles, roles
│   ├── careers/         # Career paths, skills, roadmaps, interview questions
│   ├── courses/         # Courses, lessons, enrollment, progress, certificates
│   ├── matching/        # Student-mentor matching requests and suggestions
│   ├── sessions/        # Session scheduling, availability, feedback
│   ├── progress/        # Skill assessments, milestones, learning paths, snapshots
│   ├── dashboard/       # Analytics for students, mentors, admins
│   ├── guide/           # Abia AI career guide chat (OpenRouter)
│   ├── payments/        # Paystack subscriptions, webhook, lesson unlocking
│   └── core/            # Shared permissions, exceptions, utilities
├── config/
│   ├── settings/
│   │   ├── base.py      # Shared configuration
│   │   ├── development.py
│   │   ├── test.py      # Used by pytest
│   │   └── production.py
│   ├── urls.py          # Root URL routing
│   └── wsgi.py / asgi.py
├── content/
│   ├── REVIEW.md        # How a human reviews a drafted course
│   └── courses/         # Drafted course JSON, written by draft_course
├── frontend/            # Static HTML/CSS/JS site, served alongside the API
├── manage.py
├── pytest.ini           # Points pytest at config.settings.test
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
| Certificates | `/certificates/` | my certificates, PDF download, public verify |
| Matching | `/matching/` | match requests, matches, mentor suggestions |
| Sessions | `/sessions/` | sessions, recurrences, availability, feedback |
| Progress | `/progress/` | assessments, milestones, learning paths, snapshots |
| Dashboard | `/dashboard/` | student, mentor, admin overviews |
| Guide | `/guide/` | Abia AI career guide chat |
| Payments | `/payments/` | initialize, verify, status, webhook |

Interactive docs: `/api/docs/` (Swagger UI), `/api/redoc/` (ReDoc), `/api/schema/` (OpenAPI JSON).

### Enrollments

`/api/courses/enrollments/` is read only. It lists and retrieves the current student's enrollments and returns progress through `/api/courses/enrollments/{id}/progress/`. Posting to it returns 405; use the enroll action instead:

`POST /api/courses/{id}/enroll/` enrolls the current student in that course. Re-enrolling in a course that was previously dropped reactivates the existing enrollment.

### Quizzes

`GET /api/courses/lessons/{id}/` returns the lesson with `quiz_question` and `quiz_options`, but never the answer key. Grading happens server-side on submission:

`POST /api/courses/lessons/{id}/quiz/` takes a body of `{"answer_index": 2}`. The response carries the grading result under `data.result`:

| Field | Description |
|-------|-------------|
| `correct` | Whether the submitted answer was right |
| `correct_index` | Index of the correct option |
| `feedback` | The lesson's quiz feedback text |

Quiz answers are stored on `LessonProgress` as `quiz_answered` / `quiz_correct`, written before the result is returned. A student who retries a quiz overwrites their earlier attempt, so course scoring always reads the latest attempt per lesson.

### Certificates

A student earns a certificate for a course once three things are true: the course is content reviewed, every published lesson is complete, and the average quiz score across graded lessons is at least `CERT_PASS_MARK`. A 403 on the issue endpoint names exactly which of those is missing.

| Endpoint | Method | Access | Purpose |
|----------|--------|--------|---------|
| `/api/courses/{id}/certificate/` | POST | Owner only | Issue the certificate, or return the existing one |
| `/api/certificates/` | GET | Owner only | List my certificates |
| `/api/certificates/{code}/pdf/` | GET | Owner only | Download the certificate PDF |
| `/api/certificates/verify/{code}/` | GET | Public | Confirm a certificate is genuine |

Each certificate carries a unique 16-character code generated with `secrets.token_hex(8)`, so codes are not guessable and sequential. The PDF is drawn with reportlab straight from the database on every request and never written to disk, because Render's free tier has no persistent storage. It is printed in MSA navy `#050B2E` and gold `#D4AF37`, and shows the holder's name, the course title, the issue date, the certificate code, and the public verify URL.

The public verify endpoint returns only `holder_name`, `course_title`, `issued_at` and `valid`. The email, username and user id are never serialized, so a leaked code still tells a visitor nothing beyond the name on the certificate.

### Guide

`POST /api/guide/chat/` takes the last few turns of a conversation and returns `{"reply": "..."}`. The Abia system prompt is added server-side and the API key is never sent to the browser. Input is bounded to 10 messages of 1000 characters each, and each user gets `GUIDE_DAILY_LIMIT` questions per day, counted from the `GuideUsage` rows. If OpenRouter is unconfigured the endpoint returns 503; if it is unreachable, 502, and neither leaks upstream text.

### Payments

Subscriptions are sold through Paystack. Amount and duration come from settings, never from the request body.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/payments/initialize/` | POST | Create the subscription and return the Paystack authorization URL |
| `/api/payments/verify/` | GET | Confirm a reference after the student returns from Paystack |
| `/api/payments/status/` | GET | Whether the current student has active access |
| `/api/payments/webhook/` | POST | Paystack calls this directly |

The reference is generated server-side, so a client cannot choose or replay one. Access is granted only when Paystack reports the transaction successful *and* the settled amount matches what we charged; a mismatch marks the subscription `FAILED`. Applying the same reference twice is a no-op, which makes the webhook safe to retry.

The webhook is CSRF exempt and unauthenticated because Paystack is the caller, so it authenticates with an HMAC SHA512 signature over the raw body compared with `hmac.compare_digest`. A bad or missing signature gets 401.

The first `FREE_LESSONS_PER_COURSE` lessons of a course are open to any enrolled student. Beyond that, lessons are locked until the subscription is active. A locked lesson returns 402 from the detail, quiz and complete endpoints, and its serializer blanks `content_html`, `has_quiz`, `quiz_question` and `quiz_options`, so the text never reaches the browser in the first place. When the subscription expires the lessons lock again.

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

Two areas add their own checks on top of these:

- **Certificates** are issued and listed for their owner only, and the PDF is downloadable by the owner only. The verify endpoint is deliberately public but returns no private fields.
- **Paid lessons** are served to any authenticated visitor, but a lesson past `FREE_LESSONS_PER_COURSE` returns 402 unless the requester's subscription is active.

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
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Abia guide and course drafting | required for those features |
| `GUIDE_DAILY_LIMIT` | Questions per user per day | `20` |
| `GUIDE_MAX_TOKENS` | Reply length cap | `500` |
| `PAYSTACK_SECRET_KEY` | Paystack secret key | required for payments |
| `SUBSCRIPTION_AMOUNT_KOBO` | Price in kobo | `500000` |
| `SUBSCRIPTION_DAYS` | Access window length | `30` |
| `FREE_LESSONS_PER_COURSE` | Lessons open before payment | `2` |
| `FRONTEND_BASE_URL` | Paystack return URL origin | `https://acadbot-demo.onrender.com` |
| `CERT_PASS_MARK` | Average quiz score needed to certify | `70` |
| `CERT_VERIFY_BASE_URL` | Verify URL printed on the PDF | `https://app.moresuccessacademy.com.ng/verify.html` |

Development uses `.env` (git-ignored). Production sets variables in the platform dashboard.

---

## Content Authoring

Course content is drafted by a model, reviewed by a human, and only then loaded. The two commands enforce that order, and nothing publishes unreviewed content.

```bash
# 1. Draft one course per career into content/courses/<career-slug>.json
python manage.py draft_course <career-slug>

# 2. A human reads the draft and sets "reviewed": true, per content/REVIEW.md

# 3. Load every reviewed draft
python manage.py load_reviewed_courses
```

`draft_course` asks the model for a single course matching the career, retries once if the JSON is malformed, and stops cleanly if the API rate-limits. It writes nothing until the draft passes `validate_draft`, so a bad file never reaches the database.

`load_reviewed_courses` skips any file still marked unreviewed and reports how many are waiting. Loaded courses are created or updated in place, and it sets `content_reviewed` to true, which is what makes their students eligible for certificates.

For a course that already exists in the database, review is a separate step:

```bash
python manage.py mark_reviewed <course-id>
python manage.py mark_reviewed <career-slug> <module-number>
```

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
- Certificates
- Match requests, matches, mentor suggestions
- Sessions, recurrences, availability, feedback
- Skill assessments, milestones, learning paths, progress snapshots
- Guide usage, subscriptions

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

## Frontend

The frontend is static HTML, CSS and vanilla JavaScript in `frontend/`. Django does not serve it, so it is hosted separately and calls the API across origins, which is why `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` matter in production. It resolves its API base URL at runtime in `frontend/js/api.js`:

| Host | Base URL |
|------|----------|
| `*.moresuccessacademy.com.ng` | `https://api.moresuccessacademy.com.ng` |
| anything else (local development) | `http://localhost:8000` |

So local development needs the Django server running on port 8000, and production requests go to the deployed API subdomain.

| Page | File |
|------|------|
| Landing | `frontend/index.html` |
| Courses | `frontend/courses.html` |
| Course detail, enrollment, quiz, certificate claim | `frontend/course-detail.html` |
| Dashboard, including my certificates | `frontend/dashboard.html` |
| Abia guide chat | `frontend/msa-guide.html` |
| Public certificate verify | `frontend/verify.html` |
| Paystack return | `frontend/payment-return.html` |
| Login, register | `frontend/login.html`, `frontend/register.html` |

Values returned by the API are put into the DOM with `textContent`, never `innerHTML`, so course titles and certificate names cannot inject markup.

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

### Deploying to Render

Render's free tier ignores the `Procfile`, so the `release_command` and the migrations it contains never run. Run migrations from the Build Command instead:

```
pip install -r requirements/production.txt && python manage.py collectstatic --no-input && python manage.py migrate
```

Keep the `Procfile` as the plain gunicorn web command, since that is what Render's web process uses.

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

Tests run on pytest through pytest-django. `pytest.ini` points at `config.settings.test`, which uses a throwaway database and relaxes the auth throttle limits so rate-limit tests can tighten them deliberately.

```bash
# Run the whole suite
pytest

# One file, or one test
pytest apps/payments/tests/test_payments.py
pytest apps/courses/tests/test_certificates.py::test_verify_is_public_and_leaks_nothing_private

# Check for missing migrations
python manage.py makemigrations --check --dry-run
```

| Area | File |
|------|------|
| Registration, login, CSRF, throttling | `apps/accounts/tests/` |
| Permission classes | `apps/accounts/tests/test_permissions.py` |
| Enrollment, progress, quizzes | `apps/courses/tests/test_enrollment_flow.py` |
| Certificate eligibility, PDF, verify | `apps/courses/tests/test_certificates.py` |
| Drafting and the review gate | `apps/courses/tests/test_drafting.py` |
| Guide chat, limits, upstream failures | `apps/guide/tests/test_guide_chat.py` |
| Payment init, verify, webhook, locking | `apps/payments/tests/test_payments.py` |
| Session feedback ownership | `apps/sessions/tests/test_session_feedback.py` |

The payment and guide suites stub the Paystack and OpenRouter calls at the network boundary, so they run offline and never spend real money or quota.

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
| `e5087c2` | Paystack subscriptions and lesson locking, the Abia guide app, certificates with on-the-fly PDF and public verify, and the `draft_course` / `load_reviewed_courses` content pipeline |
| `d6ef1f3` | Fix courses page layout on laptop and phone, update footer year to 2026 |
| `30d9d46` | Implement responsive navbar toggle for improved mobile navigation |
| `cd3a09a` | Remove remaining AI wording from guide and chat pages |
| `8d25424` | Match landing stats and copy to what the product does |
| `3e93f60` | Fix session feedback IDOR and broken login redirect |
| `7fa2928` | Stop leaking backend error details on 5 pages and clean up register.js |

---

## License

Internal project — More Success Academy.