# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Existing codebase already answers this: plain HTML, CSS, and vanilla ES-module JavaScript frontend (`frontend/`) against a Django REST Framework backend (`/api/`). No framework, no build step. No Stack section needed.

## Users

Primary users are More Success Academy students and the mentors who guide them, working together on the platform.

- **Students** browse courses organized by career path, enroll, work through lessons, and track progress toward a career goal.
- **Mentors** guide students; mentor-facing flows (sessions, matching, availability) exist in the backend but are not part of the v1 frontend.

## Product Purpose

MSA AcadBot helps More Success Academy students build career skills through structured, career-path-aligned courses, with AI assistance as the core differentiator. Success means a student moves from a course catalog to an enrolled, progressing learner — and, on the backend, onward to mentor-guided sessions and skill assessment.

## Positioning

"AcadBot" is the differentiator: AI-assisted learning, not just a course catalog. The product pairs structured career-path courses with AI guidance (and human mentor matching on the backend) in a way a plain course platform could not truthfully claim.

## Operating Context

- Web application: plain HTML/CSS/vanilla-JS frontend (`frontend/`) calling a Django REST Framework backend over `/api/`.
- Session-cookie authentication with a CSRF flow: `GET /api/auth/csrf/`, then send `X-CSRFToken` on state-changing requests, always with `credentials: include`.
- v1 frontend pages: login, register, courses, course-detail, dashboard. Future backend areas (matching, sessions, progress, admin) are out of the v1 frontend scope.

## Capabilities and Constraints

**Frontend capabilities (v1):**
- Registration and login/logout with field-level validation.
- Course catalog with career-slug filtering and pagination (page size 20).
- Course detail with idempotent enrollment, lesson listing, and a non-graded lesson/quiz viewer.
- Dashboard showing the user's enrollments, progress bars, and pagination.

**Constraints:**
- Frontend is not yet integrated with the backend; `API_BASE` is hardcoded to `http://localhost:8000` with a TODO to update at integration time. No mockup data exists.
- Backend response shapes are fixed by existing serializers (e.g. `me` returns the user as `data` directly; enroll returns the enrollment as `data` directly); the frontend is written to match them.
- Frontend-only work: do not modify backend code, models, serializers, or URLs.
- No framework/build step — plain HTML, CSS, and ES-module JavaScript.

## Brand Commitments

- Product name: **MSA AcadBot** (More Success Academy AcadBot); internal More Success Academy project.
- **No real logo yet.** The frontend uses a styled-text logo placeholder (structured so swapping in a real logo image is a one-line change). Do not fabricate a logo.

## Evidence on Hand

- `README.md` — product/tech overview and API surface.
- `API_DOCUMENTATION.md` — full endpoint reference.
- Backend serializers/viewsets (`apps/accounts`, `apps/courses`) — authoritative response shapes the frontend matches.
- No real user testimonials, case studies, or launch marketing content exists; do not fabricate any.

## Product Principles

1. **The bot is the point.** Keep the AI-assisted learning angle visible rather than presenting as a bare catalog.
2. **Match the real API.** Every call, field, and response shape must reflect what the backend actually routes — no invented endpoints or mockup data.
3. **Students and mentors are one platform.** Design so learner progress and mentor guidance live in the same coherent system.
4. **Ready-to-integrate, not pre-integrated.** The frontend is wired to call real endpoints at integration time; nothing is faked in the meantime.
