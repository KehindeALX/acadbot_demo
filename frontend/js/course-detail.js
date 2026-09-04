/**
 * MSA AcadBot — Course Detail Page Logic
 * Loads course details, handles enrollment, renders lessons, and provides lesson viewer
 */

import {
  getCourse,
  enrollCourse,
  getMe,
  listEnrollments,
  getEnrollmentDetail,
  getLessonDetail,
  completeLesson,
  submitQuiz,
  formatApiError,
  isAuthError,
  isNetworkError
} from './api.js';

// ============================================================
// DOM Elements
// ============================================================
const courseHeader = document.getElementById('courseHeader');
const careerBreadcrumb = document.getElementById('careerBreadcrumb');
const courseBreadcrumb = document.getElementById('courseBreadcrumb');
const courseCareerBadge = document.getElementById('courseCareerBadge');
const courseModuleBadge = document.getElementById('courseModuleBadge');
const courseTitle = document.getElementById('courseTitle');
const courseDescription = document.getElementById('courseDescription');
const courseLessonsMeta = document.getElementById('courseLessonsMeta');
const courseDurationMeta = document.getElementById('courseDurationMeta');
const courseUpdatedMeta = document.getElementById('courseUpdatedMeta');

const enrollmentSection = document.getElementById('enrollmentSection');
const enrollmentStatus = document.getElementById('enrollmentStatus');
const enrollmentProgress = document.getElementById('enrollmentProgress');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const enrollBtn = document.getElementById('enrollBtn');
const continueBtn = document.getElementById('continueBtn');
const loginPromptBtn = document.getElementById('loginPromptBtn');

const lessonsLoading = document.getElementById('lessonsLoading');
const lessonsList = document.getElementById('lessonsList');
const lessonsEmpty = document.getElementById('lessonsEmpty');

const authNav = document.getElementById('authNav');
const toastContainer = document.getElementById('toastContainer');

// Lesson Viewer Modal
const lessonOverlay = document.getElementById('lessonOverlay');
const lessonTitle = document.getElementById('lessonTitle');
const lessonMeta = document.getElementById('lessonMeta');
const lessonCloseBtn = document.getElementById('lessonCloseBtn');
const lessonProgress = document.getElementById('lessonProgress');
const lessonSteps = document.getElementById('lessonSteps');
const lessonPrevBtn = document.getElementById('lessonPrevBtn');
const lessonNextBtn = document.getElementById('lessonNextBtn');

// ============================================================
// State
// ============================================================
let course = null;
let user = null;
let enrollment = null;
let isEnrolling = false;

// Lesson viewer state
let lessonState = {
  steps: [],
  idx: 0,
  quizAnswered: {}
};

// Focus trap: remember what opened the viewer so we can restore focus on close
let lessonLastFocus = null;

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  // Get course ID from URL
  const urlParams = new URLSearchParams(window.location.search);
  const courseId = urlParams.get('id');

  if (!courseId) {
    showToast('No course specified', 'error');
    setTimeout(() => window.location.href = 'courses.html', 1500);
    return;
  }

  await checkAuthState();
  await loadCourse(courseId);
  setupEventListeners();
});

// ============================================================
// Auth State
// ============================================================
async function checkAuthState() {
  try {
    const data = await getMe();
    if (data.success && data.data) {
      user = data.data;
      renderAuthNav();
    }
  } catch (err) {
    if (isAuthError(err)) {
      renderAuthNav(); // Not logged in
    } else if (isNetworkError(err)) {
      showToast('Unable to check login status', 'warning');
    }
  }
}

function renderAuthNav() {
  if (user) {
    authNav.innerHTML = `
      <span class="navbar__user-name">${user.first_name || user.username}</span>
      <a href="dashboard.html" class="navbar__link">Dashboard</a>
      <button id="logoutBtn" class="navbar__btn">Logout</button>
    `;
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
  } else {
    authNav.innerHTML = `
      <a href="login.html" class="navbar__link navbar__btn">Sign In</a>
      <a href="register.html" class="navbar__link navbar__btn">Sign Up</a>
    `;
  }
}

async function handleLogout() {
  const { logout } = await import('./api.js');
  try {
    await logout();
    user = null;
    enrollment = null;
    renderAuthNav();
    updateEnrollmentUI();
    showToast('Logged out successfully', 'success');
  } catch (err) {
    showToast('Logout failed', 'error');
  }
}

// ============================================================
// Load Course
// ============================================================
async function loadCourse(courseId) {
  try {
    const data = await getCourse(courseId);
    course = data;
    renderCourse();
    await checkEnrollmentStatus();
  } catch (err) {
    const message = formatApiError(err);
    showToast(message, 'error');
    if (err.status === 404) {
      setTimeout(() => window.location.href = 'courses.html', 2000);
    }
  }
}

function renderCourse() {
  if (!course) return;

  // Breadcrumb
  careerBreadcrumb.textContent = course.career?.name || 'General';
  courseBreadcrumb.textContent = course.title;

  // Badges
  courseCareerBadge.textContent = course.career?.name || 'General';
  courseModuleBadge.textContent = `Module ${course.module_number || 1}`;

  // Title & Description
  courseTitle.textContent = course.title;
  courseDescription.textContent = course.description || 'No description available.';

  // Meta
  const lessonsCount = course.lessons_count || 0;
  const totalDuration = course.total_duration_minutes || 0;
  const durationHours = Math.floor(totalDuration / 60);
  const durationMins = totalDuration % 60;
  const durationStr = durationHours > 0
    ? `${durationHours}h ${durationMins}m`
    : `${durationMins}m`;

  courseLessonsMeta.innerHTML = `📖 <span>${lessonsCount}</span> lesson${lessonsCount !== 1 ? 's' : ''}`;
  courseDurationMeta.innerHTML = `⏱ <span>${durationStr}</span> total`;
  courseUpdatedMeta.innerHTML = `📅 Updated <span>${formatDate(course.updated_at)}</span>`;

  // Render lessons
  renderLessons();
}

function formatDate(dateString) {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

// ============================================================
// Enrollment
// ============================================================
async function checkEnrollmentStatus() {
  if (!user || !course) return;

  // Fetch the user's enrollments and see if this course is among them,
  // so the page shows the correct initial state (Enroll vs Continue).
  // The enroll endpoint is idempotent, so this is best-effort only.
  try {
    const data = await listEnrollments({ page: 1 });
    const results = data.results || [];
    enrollment = results.find(enr => enr.course?.id === course.id) || null;
  } catch (err) {
    if (isAuthError(err)) {
      // Session expired — treat as logged out
      user = null;
      renderAuthNav();
    }
    enrollment = null;
  }
  updateEnrollmentUI();
}

function updateEnrollmentUI() {
  // Reset all
  enrollBtn.classList.add('hidden');
  continueBtn.classList.add('hidden');
  loginPromptBtn.classList.add('hidden');
  enrollmentProgress.classList.add('hidden');

  if (!user) {
    // Not logged in
    enrollmentStatus.textContent = 'Sign in to enroll in this course';
    loginPromptBtn.classList.remove('hidden');
    loginPromptBtn.href = `login.html?redirect=course-detail.html?id=${course.id}`;
    return;
  }

  if (enrollment) {
    // Enrolled
    enrollmentStatus.textContent = enrollment.status === 'COMPLETED' ? 'Course Completed' : 'Enrolled';
    enrollmentProgress.classList.remove('hidden');
    progressBar.style.width = `${enrollment.progress_percent || 0}%`;
    enrollmentProgress.setAttribute('role', 'progressbar');
    enrollmentProgress.setAttribute('aria-valuenow', enrollment.progress_percent || 0);
    enrollmentProgress.setAttribute('aria-valuemin', '0');
    enrollmentProgress.setAttribute('aria-valuemax', '100');
    progressText.textContent = `${enrollment.progress_percent || 0}% complete`;
    continueBtn.classList.remove('hidden');
    continueBtn.textContent = enrollment.status === 'COMPLETED' ? 'Review Course' : 'Continue Learning';
  } else {
    // Not enrolled
    enrollmentStatus.textContent = 'Not enrolled';
    enrollBtn.classList.remove('hidden');
  }
}

async function handleEnroll() {
  if (isEnrolling || !course || !user) return;

  isEnrolling = true;
  enrollBtn.disabled = true;
  enrollBtn.textContent = 'Enrolling...';

  try {
    const data = await enrollCourse(course.id);

    // Backend returns the enrollment object directly as `data`:
    // { success, message: 'Enrolled successfully'|'Re-enrolled successfully', data: { enrollment } }
    // Enrolling is idempotent — re-enrollment returns 200, never an error.
    if (data.success && data.data) {
      enrollment = data.data;
      updateEnrollmentUI();
      showToast(data.message || 'Successfully enrolled!', 'success');
    } else {
      showToast(data.message || 'Enrollment failed', 'error');
    }
  } catch (err) {
    showToast(formatApiError(err), 'error');
  } finally {
    isEnrolling = false;
    enrollBtn.disabled = false;
    enrollBtn.textContent = 'Enroll Now';
  }
}

function openFirstLesson() {
  if (!course?.lessons?.length) return;
  openLessonViewer(course.lessons[0], 0);
}

/**
 * Open the first lesson the student has NOT yet completed, so "Continue
 * Learning" resumes where they left off instead of restarting at lesson 1.
 * When every lesson is done, opens the first lesson for review.
 */
async function openResumeLesson() {
  const lessons = course?.lessons || [];
  if (!lessons.length) return;

  let completedIds = new Set();
  if (enrollment?.id) {
    try {
      const detail = await getEnrollmentDetail(enrollment.id);
      const lp = detail?.data?.lesson_progress || [];
      completedIds = new Set(lp.filter(p => p.completed_at).map(p => p.lesson?.id));
    } catch (err) {
      // Fall through — without progress data we start at lesson 1.
      if (!isNetworkError(err)) {
        showToast(formatApiError(err), 'error');
      }
    }
  }

  // Lessons are ordered; find the first uncompleted one.
  const ordered = [...lessons].sort((a, b) => (a.order || 0) - (b.order || 0));
  const next = ordered.find(l => !completedIds.has(l.id)) || ordered[0];
  openLessonViewer(next, lessons.indexOf(next));
}

// ============================================================
// Lessons Rendering
// ============================================================
function renderLessons() {
  lessonsLoading.classList.add('hidden');

  if (!course?.lessons?.length) {
    lessonsEmpty.classList.remove('hidden');
    return;
  }

  lessonsList.innerHTML = '';
  lessonsList.classList.remove('hidden');

  course.lessons.forEach((lesson, index) => {
    const lessonEl = createLessonElement(lesson, index);
    lessonsList.appendChild(lessonEl);
  });
}

function createLessonElement(lesson, index) {
  const div = document.createElement('article');
  div.className = 'card lesson-card';

  const hasQuiz = lesson.has_quiz;
  const duration = lesson.duration_minutes || 0;
  const durationStr = duration > 0 ? `${duration} min` : '—';

  div.innerHTML = `
    <div class="card__body lesson-card__body">
      <div class="lesson-card__row">
        <div class="lesson-card__info">
          <span class="card__badge card__badge--draft">${index + 1}</span>
          <div style="min-width: 0;">
            <h4 class="card__title lesson-card__title">
              ${escapeHtml(lesson.title)}
            </h4>
            <div class="lesson-card__meta">
              <span>⏱ ${durationStr}</span>
              ${hasQuiz ? '<span class="card__badge card__badge--published">Quiz</span>' : ''}
            </div>
          </div>
        </div>
        <button
          class="btn btn--primary btn--sm"
          data-lesson-index="${index}"
          aria-label="Start lesson: ${escapeHtml(lesson.title)}"
        >
          ${enrollment ? 'Start' : 'Preview'}
        </button>
      </div>
    </div>
  `;

  const startBtn = div.querySelector('button');
  startBtn.addEventListener('click', () => openLessonViewer(lesson, index));

  return div;
}

// ============================================================
// Lesson Viewer (adapted from index.html)
// ============================================================
function openLessonViewer(lesson, index) {
  // Build steps. If the student is enrolled, we fetch the lesson detail so the
  // quiz can be graded against the real answer key; otherwise it's a preview.
  lessonState = {
    lessonId: lesson.id,
    isGraded: false,
    correctIndex: null,
    quizFeedback: '',
    steps: parseLessonContent(lesson),
    idx: 0,
    quizAnswered: {}
  };

  lessonTitle.textContent = lesson.title;
  lessonMeta.textContent = `Lesson ${index + 1} of ${course.lessons.length} · ${course.title}`;

  renderLessonProgress();
  renderLessonStep();
  lessonOverlay.classList.add('active');
  document.body.style.overflow = 'hidden';

  // Focus trap: remember the opener and move focus into the modal
  lessonLastFocus = document.activeElement;
  lessonOverlay.setAttribute('aria-hidden', 'false');
  (lessonCloseBtn || lessonOverlay).focus();

  // Enrolled students get the real quiz answer key + feedback from the
  // lesson-detail endpoint (the list endpoint deliberately omits it).
  if (enrollment?.id && lesson.has_quiz) {
    loadLessonDetail(lesson.id);
  }
}

async function loadLessonDetail(lessonId) {
  try {
    const detail = await getLessonDetail(lessonId);
    lessonState.isGraded = true;
    lessonState.correctIndex = detail.quiz_correct_index;
    lessonState.quizFeedback = detail.quiz_feedback || '';
    // Re-render only if we're still on this lesson and a quiz is visible
    if (lessonState.lessonId === lessonId && lessonOverlay.classList.contains('active')) {
      renderLessonStep();
    }
  } catch (err) {
    // Preview fallback — quiz stays ungraded rather than blocking the lesson.
    if (!isNetworkError(err)) {
      showToast(formatApiError(err), 'error');
    }
  }
}

function parseLessonContent(lesson) {
  // The lesson has content_html which is the full lesson.
  // Build a single content step, plus a quiz step if one exists. The quiz is
  // graded once the lesson detail (answer key) has been fetched for an
  // enrolled student; otherwise it renders as an honest, ungraded preview.
  const steps = [];

  // Main content step
  steps.push({
    h: lesson.title,
    body: lesson.content_html || '<p>No content available for this lesson.</p>'
  });

  // Quiz step
  if (lesson.has_quiz && lesson.quiz_question && lesson.quiz_options) {
    steps.push({
      h: 'Knowledge Check',
      quiz: {
        q: lesson.quiz_question,
        opts: lesson.quiz_options,
      }
    });
  }

  return steps;
}

function closeLessonViewer() {
  lessonOverlay.classList.remove('active');
  lessonOverlay.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  // Return focus to whatever opened the viewer
  if (lessonLastFocus && lessonLastFocus.focus) {
    lessonLastFocus.focus();
  }
  lessonLastFocus = null;
}

// Keep keyboard focus inside the modal while it is open
function trapLessonFocus(e) {
  if (!lessonOverlay.classList.contains('active')) return;

  if (e.key === 'Tab') {
    const focusables = lessonOverlay.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

function renderLessonProgress() {
  lessonProgress.innerHTML = '';
  lessonState.steps.forEach((_, i) => {
    const span = document.createElement('span');
    if (i < lessonState.idx) span.classList.add('done');
    lessonProgress.appendChild(span);
  });
}

function renderLessonStep() {
  const step = lessonState.steps[lessonState.idx];
  const isLast = lessonState.idx === lessonState.steps.length - 1;

  let html = `<div class="lesson-step active">`;

  if (step.h) html += `<h4>${step.h}</h4>`;
  if (step.body) html += `<div>${step.body}</div>`;

  if (step.quiz) {
    const q = step.quiz;
    const answered = lessonState.quizAnswered[lessonState.idx];
    const graded = lessonState.isGraded && lessonState.correctIndex !== null;

    html += `<div class="lesson-quiz"><div class="lesson-quiz-q">${escapeHtml(q.q)}</div>`;
    q.opts.forEach((opt, i) => {
      let cls = 'lesson-quiz-opt';
      if (answered !== undefined && i === answered) cls += ' selected';
      if (graded && answered !== undefined) {
        if (i === lessonState.correctIndex) cls += ' correct';
        else if (i === answered) cls += ' wrong';
      }
      html += `<button class="${cls}" onclick="answerQuiz(${i})" ${answered !== undefined ? 'disabled' : ''}>${escapeHtml(opt)}</button>`;
    });
    if (answered !== undefined) {
      let fb = 'Answer recorded — full quiz grading is available once you\'re enrolled and working through the lesson.';
      let fbClass = '';
      if (graded) {
        const isCorrect = answered === lessonState.correctIndex;
        fb = isCorrect
          ? `Correct! ${lessonState.quizFeedback || 'Nice work.'}`
          : `Not quite — the correct answer is highlighted. ${lessonState.quizFeedback || ''}`;
        fbClass = isCorrect ? ' right' : ' wrong';
      }
      html += `<div class="lesson-quiz-fb show${fbClass}" id="quizFb">${escapeHtml(fb)}</div>`;
    }
    html += `</div>`;
  }

  html += `</div>`;
  lessonSteps.innerHTML = html;

  // Update nav buttons
  lessonPrevBtn.disabled = lessonState.idx === 0;

  if (step.quiz && lessonState.quizAnswered[lessonState.idx] === undefined) {
    lessonNextBtn.textContent = 'Answer to continue';
    lessonNextBtn.disabled = true;
  } else {
    lessonNextBtn.disabled = false;
    lessonNextBtn.textContent = isLast ? 'Finish ✓' : 'Continue →';
  }
}

// Make answerQuiz globally accessible for inline onclick
window.answerQuiz = function(i) {
  if (lessonState.quizAnswered[lessonState.idx] !== undefined) return; // already answered
  lessonState.quizAnswered[lessonState.idx] = i;
  renderLessonStep();

  // Persist the answer for enrolled students so their progress reflects it.
  // Grading is shown locally from the answer key; this records it server-side.
  if (enrollment?.id && lessonState.isGraded) {
    submitQuiz(lessonState.lessonId, i).catch(() => {
      // Best-effort — a failed submission shouldn't block the lesson.
    });
  }
};

function lessonNext() {
  if (lessonState.idx < lessonState.steps.length - 1) {
    lessonState.idx++;
    renderLessonProgress();
    renderLessonStep();
  } else {
    showLessonComplete();
  }
}

function lessonPrev() {
  if (lessonState.idx > 0) {
    lessonState.idx--;
    renderLessonProgress();
    renderLessonStep();
  }
}

function showLessonComplete() {
  lessonSteps.innerHTML = `
    <div class="lesson-complete">
      <div class="lc-icon">🎉</div>
      <h4>Lesson Complete!</h4>
      <p>Great work. Your progress is saved. Close the lesson and continue with the next one, or return to the course.</p>
    </div>
  `;
  lessonNav.style.display = 'none';
  lessonProgress.querySelectorAll('span').forEach(s => s.classList.add('done'));

  // Enrolled students: record completion on the backend, then refresh the
  // course progress bar so it reflects the new state.
  if (enrollment?.id && lessonState.lessonId) {
    completeLesson(lessonState.lessonId)
      .then(refreshProgress)
      .catch(() => {
        // Best-effort — if this fails, the lesson viewer still closed cleanly.
      });
  }
}

// Re-fetch the enrollment detail to refresh the progress bar after a lesson
// is completed (the server recomputes progress_percent).
async function refreshProgress() {
  if (!enrollment?.id) return;
  try {
    const detail = await getEnrollmentDetail(enrollment.id);
    const data = detail?.data;
    if (data) {
      enrollment = { ...enrollment, ...data };
      updateEnrollmentUI();
    }
  } catch (err) {
    // Non-blocking — the progress bar refresh is best-effort.
  }
}

// ============================================================
// Event Listeners
// ============================================================
function setupEventListeners() {
  // Enroll button
  enrollBtn.addEventListener('click', handleEnroll);

  // Continue button — resume from the next uncompleted lesson
  continueBtn.addEventListener('click', (e) => {
    e.preventDefault();
    openResumeLesson();
  });

  // Lesson viewer
  lessonCloseBtn.addEventListener('click', closeLessonViewer);
  lessonPrevBtn.addEventListener('click', lessonPrev);
  lessonNextBtn.addEventListener('click', lessonNext);

  // Close on overlay click
  lessonOverlay.addEventListener('click', (e) => {
    if (e.target === lessonOverlay) {
      closeLessonViewer();
    }
  });

  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (!lessonOverlay.classList.contains('active')) return;

    trapLessonFocus(e);

    if (e.key === 'Escape') {
      closeLessonViewer();
    } else if (e.key === 'ArrowRight' && !lessonNextBtn.disabled) {
      lessonNext();
    } else if (e.key === 'ArrowLeft' && !lessonPrevBtn.disabled) {
      lessonPrev();
    }
  });
}

// ============================================================
// Utilities
// ============================================================
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <span class="toast__icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : type === 'warning' ? '⚠' : 'ℹ'}</span>
    <div class="toast__content">
      <div class="toast__message">${message}</div>
    </div>
  `;

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}