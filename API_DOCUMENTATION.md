# MSA AcadBot API Documentation

**Base URL:** `http://localhost:8000/api/` (development)  
**Authentication:** Session-based with CSRF protection  
**Content-Type:** `application/json`

---

## Authentication

All API endpoints (except public ones) require session authentication. The flow:

1. **Get CSRF token** — `GET /api/auth/csrf/`
2. **Register** — `POST /api/auth/register/`
3. **Login** — `POST /api/auth/login/` (sets session cookie)
4. **Authenticated requests** — Include session cookie + `X-CSRFToken` header

### CSRF Token

```http
GET /api/auth/csrf/
```

**Response:**
```json
{
  "csrfToken": "abc123..."
}
```

Include this token in subsequent requests:
```
X-CSRFToken: abc123...
```

---

## Error Format

All error responses follow this structure:

```json
{
  "success": false,
  "error": {
    "code": 400,
    "message": "Human-readable error message",
    "details": {}
  }
}
```

| Code | Meaning |
|------|---------|
| 400 | Validation error / bad request |
| 401 | Not authenticated |
| 403 | Not authorized |
| 404 | Not found |
| 500 | Server error |

---

## Core Endpoints

### Authentication (`/api/auth/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| POST | `/register/` | Register new user (student or mentor) | Public |
| POST | `/login/` | Login with email/password | Public |
| POST | `/logout/` | Logout current user | Authenticated |
| GET | `/me/` | Get current user profile | Authenticated |
| PATCH | `/me/` | Update current user profile | Authenticated |

#### Register Request
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepass123",
  "password_confirm": "securepass123",
  "role": "student",  // or "mentor"
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}
```

#### Register/Login Response
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "avatar": null,
    "bio": "",
    "timezone": "UTC",
    "role": "student",
    "role_display": "Student",
    "is_verified": false,
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-15T10:30:00Z",
    "profile": { ... }
  }
}
```

#### Update Profile (PATCH /me/)
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "avatar": "base64_or_file",
  "bio": "Software engineer",
  "timezone": "America/New_York"
}
```

---

### Student Profile (`/api/auth/students/profile/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get own profile |
| PUT/PATCH | `/` | Update own profile |

**Profile Fields:**
- `career` — Selected career path (read-only nested)
- `career_id` — Career ID for updates
- `current_stage` — Current roadmap stage (read-only nested)
- `current_stage_id` — Stage ID for updates
- `skills_data` — JSON object of skill levels
- `onboarding_complete` — Boolean
- `preferred_schedule` — JSON schedule preferences
- `learning_goals` — Text field
- `progress_percentage` — Computed field

---

### Mentor Profile (`/api/auth/mentors/profile/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Get own profile |
| PUT/PATCH | `/` | Update own profile |
| GET | `/me/` | Get own profile (alias) |
| PATCH | `/me/` | Update own profile (alias) |

**Profile Fields:**
- `expertise_careers` — Array of career objects (read-only)
- `expertise_career_ids` — Career IDs for updates
- `hourly_rate` — Decimal
- `availability_data` — JSON availability
- `rating` — Average rating (read-only)
- `total_sessions` — Count (read-only)
- `is_verified` — Admin-verified (read-only)
- `is_available` — Accepting matches
- `bio` — Text

---

### Public Mentor Listings (`/api/auth/mentors/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List verified, available mentors |
| GET | `/{id}/` | Get mentor details |

**Query Parameters:**
- `expertise_careers` — Filter by career ID
- `search` — Search name/bio
- `ordering` — `-rating`, `-total_sessions`, `hourly_rate`

---

## Careers (`/api/careers/`)

All endpoints public (AllowAny).

### Career List & Detail

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List active careers (lightweight) |
| GET | `/{slug}/` | Get career with nested skills, roadmap, questions |

**List Response:**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "slug": "software-engineering",
      "name": "Software Engineering",
      "icon": "code",
      "tag": "tech",
      "color": "#007bff",
      "description": "Build applications...",
      "order": 1,
      "skills_count": 12,
      "roadmap_stages_count": 6,
      "interview_questions_count": 25
    }
  ]
}
```

**Detail Response** adds:
- `skills` — Array of CareerSkill objects
- `roadmap_stages` — Array of RoadmapStage objects
- `interview_questions` — Array of InterviewQuestion objects

### Career Skills (`/api/careers/skills/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all skills |
| GET | `/{id}/` | Get skill details |

**Filters:** `career`, `is_core`

### Roadmap Stages (`/api/careers/roadmap/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all stages |
| GET | `/{id}/` | Get stage details |

**Filters:** `career`

### Interview Questions (`/api/careers/interview-questions/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all questions |
| GET | `/{id}/` | Get question details |

**Filters:** `career`, `difficulty` (easy/medium/hard)

### Career-Specific Actions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/{slug}/skills/` | Core skills for a career |
| GET | `/{slug}/roadmap/` | Active roadmap stages |
| GET | `/{slug}/interview-questions/` | Active interview questions |

---

## Courses (`/api/courses/`)

### Course Catalog

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List published courses | Public |
| GET | `/{id}/` | Get course with lessons | Public |

**Query Parameters:**
- `career` — Filter by career slug

### Enrollment (`/api/courses/enrollments/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List own enrollments | Student |
| GET | `/{id}/` | Get enrollment with lesson progress | Student |
| GET | `/{id}/progress/` | Detailed progress for enrollment | Student |

### Enroll in Course

```http
POST /api/courses/{id}/enroll/
```

**Response:**
```json
{
  "success": true,
  "message": "Enrolled successfully",
  "data": {
    "id": 1,
    "course": { ... },
    "status": "active",
    "enrolled_at": "2026-01-15T10:30:00Z",
    "started_at": null,
    "completed_at": null,
    "progress_percent": 0,
    "last_accessed_at": null
  }
}
```

### Lessons (`/api/courses/lessons/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List lessons (filtered by course) | Student |
| GET | `/{id}/` | Get lesson with quiz answer | Student |
| POST | `/{id}/complete/` | Mark lesson complete | Student |
| POST | `/{id}/quiz/` | Submit quiz answer | Student |

#### Complete Lesson
```http
POST /api/courses/lessons/{id}/complete/
```

#### Submit Quiz
```json
{
  "answer_index": 2
}
```

**Quiz Response:**
```json
{
  "success": true,
  "message": "Quiz submitted",
  "data": {
    "progress": { ... },
    "result": {
      "correct": true,
      "correct_index": 2,
      "feedback": "Great job!"
    }
  }
}
```

---

## Matching (`/api/matching/`)

### Match Requests (`/api/matching/requests/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| POST | `/` | Create match request | Student |
| GET | `/` | List own requests | Student |
| GET | `/{id}/` | Get request details | Student |
| GET | `/{id}/suggestions/` | Get mentor suggestions | Student |
| POST | `/{id}/auto-match/` | Auto-create best match | Student |
| POST | `/{id}/refresh-suggestions/` | Refresh suggestions | Student |

#### Create Match Request
```json
{
  "preferred_career_ids": [1, 2],
  "preferred_schedule": {
    "days": ["monday", "wednesday"],
    "time_range": "18:00-21:00",
    "timezone": "America/New_York"
  },
  "notes": "Looking for backend mentorship"
}
```

### Matches (`/api/matching/matches/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List own matches | Student/Mentor/Admin |
| GET | `/{id}/` | Get match details | Owner/Mentor/Admin |
| POST | `/{id}/accept/` | Accept match (mentor) | Mentor |
| POST | `/{id}/decline/` | Decline match (mentor) | Mentor |
| POST | `/{id}/cancel/` | Cancel match (student/mentor) | Owner/Mentor |

### Mentor Suggestions (`/api/matching/suggestions/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List suggestions for own requests | Student |

---

## Sessions (`/api/sessions/`)

### Sessions (`/api/sessions/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| POST | `/` | Create session | Student/Mentor (match owner) |
| GET | `/` | List own sessions | Student/Mentor/Admin |
| GET | `/{id}/` | Get session details | Owner/Mentor/Admin |
| PATCH | `/{id}/` | Update session (reschedule) | Owner/Mentor |
| POST | `/{id}/start/` | Start session (mentor) | Mentor |
| POST | `/{id}/complete/` | Complete with feedback | Student/Mentor |
| POST | `/{id}/cancel/` | Cancel session | Student/Mentor |
| POST | `/{id}/reschedule/` | Reschedule session | Student/Mentor |
| GET | `/upcoming/` | Upcoming sessions | Student/Mentor |
| GET | `/past/` | Past sessions | Student/Mentor |

#### Create Session
```json
{
  "match_id": 5,
  "scheduled_at": "2026-01-20T19:00:00Z",
  "duration_minutes": 60,
  "meeting_link": "https://meet.example.com/abc",
  "meeting_id": "abc-123",
  "notes": "First session - intro"
}
```

#### Complete Session
```json
{
  "feedback": "Great session, learned a lot",
  "rating": 5,
  "notes": "Covered API design"
}
```

#### Reschedule Session
```json
{
  "scheduled_at": "2026-01-22T19:00:00Z",
  "duration_minutes": 90
}
```

### Session Recurrences (`/api/sessions/recurrences/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List recurrences for own sessions | Student/Mentor/Admin |
| POST | `/` | Create recurrence | Student/Mentor |
| GET | `/{id}/` | Get recurrence | Owner/Mentor/Admin |
| PUT/PATCH | `/{id}/` | Update recurrence | Owner/Mentor |
| DELETE | `/{id}/` | Delete recurrence | Owner/Mentor |

**Recurrence Fields:**
- `session` — Parent session (read-only)
- `frequency` — weekly, biweekly, monthly
- `end_date` — Optional end date
- `is_active` — Boolean

### Mentor Availability (`/api/sessions/availability/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List own availability | Mentor |
| POST | `/` | Create availability slot | Mentor |
| GET | `/{id}/` | Get availability | Mentor |
| PUT/PATCH | `/{id}/` | Update availability | Mentor |
| DELETE | `/{id}/` | Delete availability | Mentor |
| GET | `/my-schedule/` | Weekly recurring schedule | Mentor |
| DELETE | `/clear-all/` | Clear all recurring slots | Mentor |

#### Create Availability
```json
{
  "day_of_week": 1,  // 0=Monday, 6=Sunday
  "start_time": "18:00:00",
  "end_time": "21:00:00",
  "timezone": "America/New_York",
  "is_recurring": true,
  "specific_date": null,
  "is_available": true
}
```

### Public Mentor Availability (`/api/sessions/mentors/{mentor_id}/availability/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List verified mentor's availability | Authenticated |

### Session Feedback (`/api/sessions/{session_id}/feedback/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List feedback for session | Student/Mentor |
| POST | `/` | Create/update feedback | Student/Mentor |
| GET | `/{id}/` | Get feedback | Student/Mentor |
| PUT/PATCH | `/{id}/` | Update feedback | Author |
| DELETE | `/{id}/` | Delete feedback | Author |

#### Create Feedback
```json
{
  "feedback_type": "student",  // or "mentor"
  "rating": 5,
  "strengths": "Clear explanations",
  "areas_for_improvement": "More examples",
  "additional_comments": "Very helpful",
  "is_shared": true
}
```

---

## Progress (`/api/progress/`)

### Skill Assessments (`/api/progress/skills/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List own assessments | Student |
| POST | `/` | Create/update assessment | Student |
| GET | `/{id}/` | Get assessment | Student |
| PUT/PATCH | `/{id}/` | Update assessment | Student |
| GET | `/by-career/` | Grouped by career | Student |
| GET | `/summary/` | Statistics summary | Student |

#### Create Assessment
```json
{
  "career_skill_id": 3,
  "self_rated_level": 3,
  "assessment_type": "self",  // self, mentor, peer
  "evidence": "Built 3 REST APIs",
  "notes": "Comfortable with DRF"
}
```

**Assessment Types:**
- `self` — Requires `self_rated_level` (1-5)
- `mentor` — Requires `assessed_level` (1-5), sets `assessed_by` to current user
- `peer` — Requires `assessed_level` (1-5), sets `assessed_by` to current user

### Milestones (`/api/progress/milestones/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List own milestones | Student |
| POST | `/` | Create milestone | Student |
| GET | `/{id}/` | Get milestone | Student |
| PUT/PATCH | `/{id}/` | Update milestone | Student |
| DELETE | `/{id}/` | Delete milestone | Student |
| GET | `/by-type/` | Grouped by type | Student |
| GET | `/recent/` | Last 10 milestones | Student |

#### Create Milestone
```json
{
  "career_id": 1,
  "title": "Deployed first app",
  "description": "Deployed Django app to Render",
  "milestone_type": "project",  // project, certification, job, custom
  "achieved_at": "2026-01-15",
  "metadata": { "url": "https://example.com" },
  "is_public": true
}
```

### Learning Path (`/api/progress/learning-path/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List own learning paths | Student |
| POST | `/` | Create learning path | Student |
| GET | `/{career_id}/` | Get path for career | Student |
| PATCH | `/{career_id}/` | Update path (advance stage) | Student |
| POST | `/{career_id}/advance/` | Advance to next stage | Student |
| POST | `/{career_id}/set-stage/` | Set specific stage | Student |

#### Create Learning Path
```json
{
  "career_id": 1,
  "current_stage_id": 2,
  "target_completion_date": "2026-06-01",
  "is_active": true
}
```

#### Set Stage
```json
{
  "stage_id": 4
}
```

### Progress Snapshots (`/api/progress/snapshots/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/` | List own snapshots | Student |
| GET | `/{id}/` | Get snapshot | Student |

**Snapshot Fields (read-only):**
- `career` — Career object
- `courses_completed`, `courses_in_progress`
- `lessons_completed`, `total_lesson_time_minutes`
- `sessions_completed`, `total_session_minutes`
- `skills_assessed`, `average_skill_level`
- `milestones_achieved`
- `learning_path_progress`
- `snapshot_date`

### Progress Summary (`/api/progress/summary/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/summary/` | Comprehensive dashboard data | Student |
| POST | `/generate-snapshot/` | Generate new snapshot | Student |

#### Generate Snapshot
```json
{
  "career_id": 1  // optional, uses active learning path if omitted
}
```

**Summary Response:**
```json
{
  "success": true,
  "data": {
    "career": { ... },
    "learning_path": { ... },
    "skill_assessments": [ ... ],
    "milestones": [ ... ],
    "recent_snapshots": [ ... ],
    "total_skills_assessed": 8,
    "average_skill_level": "3.25",
    "milestones_count": 5,
    "courses_completed": 3,
    "sessions_completed": 12,
    "learning_path_progress": 45.5
  }
}
```

---

## Dashboard (`/api/dashboard/`)

### Student Dashboard (`/api/dashboard/student/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/overview/` | Complete dashboard overview | Student |
| GET | `/career-progress/` | Detailed career progress | Student |
| GET | `/activity/` | Activity timeline | Student |

**Overview Response:**
```json
{
  "success": true,
  "data": {
    "learning_path": { ... },
    "active_match": { ... },
    "upcoming_sessions": [ ... ],
    "recent_sessions": [ ... ],
    "in_progress_courses": [ ... ],
    "completed_courses": [ ... ],
    "assessed_skills_count": 8,
    "average_skill_level": "3.25",
    "recent_milestones": [ ... ],
    "match_request": { ... },
    "streak_days": 7
  }
}
```

**Career Progress Response:**
```json
{
  "success": true,
  "data": {
    "career": { ... },
    "course_progress": [
      { "course": {...}, "progress_percent": 60, "lessons_completed": 6, "total_lessons": 10 }
    ],
    "skill_progress": [
      { "skill": {...}, "self_rated": 3, "mentor_rated": 4 }
    ],
    "roadmap_progress": [
      { "stage": {...}, "completed": true, "completed_at": "2026-01-10" }
    ]
  }
}
```

**Activity Response:**
```json
{
  "success": true,
  "data": [
    {
      "type": "lesson_completed",
      "title": "Completed: Django Models",
      "description": "Finished lesson 3 of Backend Fundamentals",
      "date": "2026-01-15T14:30:00Z",
      "status": "completed",
      "metadata": { "lesson_id": 12, "course_id": 3 }
    }
  ]
}
```

### Mentor Dashboard (`/api/dashboard/mentor/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/overview/` | Mentor dashboard overview | Mentor |
| GET | `/students/` | List matched students | Mentor |
| GET | `/schedule/` | Weekly schedule + upcoming sessions | Mentor |
| GET | `/earnings/` | Earnings summary | Mentor |

**Overview Response:**
```json
{
  "success": true,
  "data": {
    "active_students_count": 5,
    "pending_matches_count": 2,
    "upcoming_sessions": [ ... ],
    "monthly_sessions_count": 8,
    "total_sessions_count": 45,
    "average_rating": "4.8",
    "mentor_profile": { ... }
  }
}
```

**Students Response:**
```json
{
  "success": true,
  "data": [
    {
      "student": { ... },
      "career": { ... },
      "total_sessions": 12,
      "last_session": { ... },
      "match_since": "2025-11-15T10:00:00Z"
    }
  ]
}
```

**Earnings Response:**
```json
{
  "success": true,
  "data": {
    "period": "monthly",
    "completed_sessions": 8,
    "total_minutes": 480,
    "total_hours": "8.0",
    "hourly_rate": "75.00",
    "estimated_earnings": "600.00"
  }
}
```

### Admin Dashboard (`/api/dashboard/admin/`)

| Method | Endpoint | Description | Permissions |
|--------|----------|-------------|-------------|
| GET | `/overview/` | Platform overview | Admin |
| GET | `/career-distribution/` | Users/enrollments by career | Admin |
| GET | `/completion-rates/` | Course completion rates | Admin |
| GET | `/engagement/` | Engagement metrics | Admin |

**Overview Response:**
```json
{
  "success": true,
  "data": {
    "users": {
      "total_students": 150,
      "total_mentors": 25,
      "new_this_week": 12,
      "active_this_month": 89
    },
    "matches": {
      "total": 89,
      "active": 67,
      "pending": 12,
      "completed": 34
    },
    "sessions": {
      "total": 456,
      "completed": 398,
      "upcoming": 23,
      "this_month": 78
    },
    "courses": {
      "total": 24,
      "published": 20,
      "total_enrollments": 567
    },
    "recent_registrations": [ ... ]
  }
}
```

---

## Permissions Summary

| Permission Class | Applies To |
|------------------|------------|
| `AllowAny` | Career catalog, public mentor listings, auth endpoints |
| `IsAuthenticated` | All other endpoints |
| `IsStudent` | Student-only: enrollments, lessons, match requests, progress |
| `IsMentor` | Mentor-only: availability, accept/decline matches, start sessions |
| `IsOwnerOrReadOnly` | Profile updates (owner only) |
| `IsOwnerOrMentorOrAdmin` | Sessions, matches, recurrences (owner, mentor, or admin) |
| `IsAdmin` | Admin dashboard endpoints |

---

## Query Patterns

### Pagination
All list endpoints use page-number pagination (default 20 per page):
```
?page=2&page_size=50
```

### Filtering
Use `filterset_fields` on each endpoint:
```
/api/courses/?career=software-engineering
/api/careers/skills/?career=1&is_core=true
/api/matching/matches/?status=active
```

### Search
Where `search_fields` defined:
```
/api/auth/mentors/?search=python
```

### Ordering
Where `ordering_fields` defined:
```
/api/auth/mentors/?ordering=-rating
/api/courses/?ordering=title
```

---

## Schema & Interactive Docs

- **OpenAPI Schema:** `GET /api/schema/`
- **Swagger UI:** `GET /api/docs/`
- **ReDoc:** `GET /api/redoc/`

---

## Rate Limiting

Not currently configured. Recommended for production:
- Auth endpoints: 10 req/min
- Read endpoints: 100 req/min
- Write endpoints: 30 req/min

---

## Versioning

Current version: `v1` (implicit in URL structure). Future versions will use `/api/v2/` prefix.

---

## Webhooks (Planned)

Not yet implemented. Planned events:
- `match.created`
- `match.accepted`
- `session.completed`
- `enrollment.created`
- `progress.snapshot.generated`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-15 | Initial release |