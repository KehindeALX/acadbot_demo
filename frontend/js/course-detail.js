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
  completeLesson,
  submitQuiz,
  initializePayment,
  getPaymentStatus,
  safeErrorMessage,
  isAuthError,
  isNetworkError
} from './api.js';
import { initNavbar } from './navbar.js';

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
const certBtn = document.getElementById('certificateBtn');
const subscribeBtn = document.getElementById('subscribeBtn');
const accessStatus = document.getElementById('accessStatus');

const lessonsLoading = document.getElementById('lessonsLoading');
const lessonsList = document.getElementById('lessonsList');
const lessonsEmpty = document.getElementById('lessonsEmpty');

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
let isSubscribing = false;
let hasPaidAccess = false;

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

  user = await initNavbar();
  await loadCourse(courseId);
  setupEventListeners();
});

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
    const message = safeErrorMessage(err);
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
      // Session expired — treat as logged out and re-render navbar as guest
      user = null;
      initNavbar();
    }
    enrollment = null;
  }
  await loadPaidAccess();
  updateEnrollmentUI();
  // Lessons re-render now that enrollment status is known, so the list shows
  // accurate "Preview" vs "Start" buttons (renderCourse() ran before this).
  renderLessons();
}

// ============================================================
// Paid Access
// ============================================================

/**
 * Ask the server whether this student has paid access. The server is the only
 * authority on payment status — the page never infers it from anything else.
 */
async function loadPaidAccess() {
  hasPaidAccess = false;
  if (!user) return;

  try {
    const data = await getPaymentStatus();
    hasPaidAccess = data?.data?.active === true;
  } catch (err) {
    if (isAuthError(err)) {
      user = null;
      initNavbar();
    }
    hasPaidAccess = false;
  }
}

function hasLockedLessons() {
  return (course?.lessons || []).some(lesson => lesson.is_locked);
}

function renderCertificate(cert) {
  const panel = document.getElementById('certificatePanel');
  if (!panel) return;
  panel.textContent = '';

  const card = document.createElement('div');
  card.className = 'cert-card';

  const info = document.createElement('div');
  const title = document.createElement('h3');
  title.className = 'cert-card__title';
  title.textContent = 'Certificate Earned';
  const meta = document.createElement('p');
  meta.className = 'cert-card__meta';
  meta.textContent = `${cert.course_title} — issued ${new Date(cert.issued_at).toLocaleDateString()}`;
  const code = document.createElement('p');
  code.className = 'cert-card__meta cert-card__code';
  code.textContent = `ID: ${cert.code}`;
  info.append(title, meta, code);

  const link = document.createElement('a');
  link.href = certificatePdfUrl(cert.code);
  link.target = '_blank';
  link.rel = 'noopener';
  link.className = 'btn btn--primary';
  link.style.background = '#D4AF37';
  link.style.color = '#050B2E';
  link.textContent = 'Download PDF';

  card.append(info, link);
  panel.appendChild(card);

  if (certBtn) {
    certBtn.classList.add('hidden');
  }
}

function renderAccessStatus() {
  if (!user || !hasLockedLessons()) {
    accessStatus.classList.add('hidden');
    accessStatus.innerHTML = '';
    return;
  }

  accessStatus.classList.remove('hidden');

  if (hasPaidAccess) {
    accessStatus.className = 'access-status access-status--active';
    accessStatus.innerHTML = `
      <div class="access-status__title">Full access is on</div>
      <div class="access-status__message">Every lesson and quiz in this course is unlocked.</div>
    `;
    return;
  }

  accessStatus.className = 'access-status access-status--locked';
  accessStatus.innerHTML = `
    <div class="access-status__title">Some lessons are locked</div>
    <div class="access-status__message">
      The first lessons of every course are free to read. Unlock the rest with one subscription.
    </div>
    <div class="access-status__meta">Enrolling stays free, and nothing you have read so far is taken away.</div>
  `;
}

async function handleSubscribe() {
  if (isSubscribing || !user) return;

  isSubscribing = true;
  subscribeBtn.disabled = true;
  subscribeBtn.textContent = 'Opening payment...';

  try {
    const data = await initializePayment();
    const authorizationUrl = data?.data?.authorization_url;

    if (!authorizationUrl) {
      showToast('We could not start the payment. Please try again.', 'error');
      return;
    }

    sessionStorage.setItem('pendingCourseId', String(course.id));
    window.location.href = authorizationUrl;
  } catch (err) {
    showToast(paymentErrorMessage(err), 'error');
    isSubscribing = false;
    subscribeBtn.disabled = false;
    subscribeBtn.textContent = 'Unlock All Lessons';
  }
}

/**
 * Payment failures have their own honest copy. safeErrorMessage would hide the
 * server's reason behind a generic line, and here the reason is the point.
 */
function paymentErrorMessage(err) {
  if (err.isNetworkError) {
    return 'Unable to reach the server. Check your connection and try again.';
  }
  if ([502, 503].includes(err.status) && err.message) return err.message;
  return 'We could not start the payment. Please try again in a moment.';
}

function updateEnrollmentUI() {
  // Reset all
  enrollBtn.classList.add('hidden');
  continueBtn.classList.add('hidden');
  loginPromptBtn.classList.add('hidden');
  subscribeBtn.classList.add('hidden');
  enrollmentProgress.classList.add('hidden');

  if (!user) {
    // Not logged in
    enrollmentStatus.textContent = 'Sign in to enroll in this course';
    loginPromptBtn.classList.remove('hidden');
    loginPromptBtn.href = `login.html?redirect=course-detail.html?id=${course.id}`;
    renderAccessStatus();
    return;
  }

  if (certBtn) {
    certBtn.classList.add('hidden');
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

    if (course.content_reviewed && enrollment.status === 'COMPLETED' && certBtn) {
      certBtn.classList.remove('hidden');
    }
  } else {
    // Not enrolled
    enrollmentStatus.textContent = 'Not enrolled';
    enrollBtn.classList.remove('hidden');
  }

  if (hasLockedLessons() && !hasPaidAccess) {
    subscribeBtn.classList.remove('hidden');
  }

  renderAccessStatus();
}

async function handleEnroll() {
  if (isEnrolling || !course || !user) return;

  isEnrolling = true;
  enrollBtn.disabled = true;
  enrollBtn.textContent = 'Enrolling...';
  setLessonButtonsDisabled(true);

  try {
    const data = await enrollCourse(course.id);

    // Backend returns the enrollment object directly as `data`:
    // { success, message: 'Enrolled successfully'|'Re-enrolled successfully', data: { enrollment } }
    // Enrolling is idempotent — re-enrollment returns 200, never an error.
    if (data.success && data.data) {
      enrollment = data.data;
      updateEnrollmentUI();
      renderLessons(); // Flip lesson buttons from "Preview" to "Start" immediately.
      showToast(data.message || 'Successfully enrolled!', 'success');
    } else {
      showToast(data.message || 'Enrollment failed', 'error');
    }
  } catch (err) {
    showToast(safeErrorMessage(err), 'error');
  } finally {
    isEnrolling = false;
    enrollBtn.disabled = false;
    enrollBtn.textContent = 'Enroll Now';
    setLessonButtonsDisabled(false);
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
        showToast(safeErrorMessage(err), 'error');
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
  const isLocked = lesson.is_locked === true;
  div.className = isLocked
    ? 'card lesson-card lesson-card--locked'
    : 'card lesson-card';

  const hasQuiz = lesson.has_quiz;
  const duration = lesson.duration_minutes || 0;
  const durationStr = duration > 0 ? `${duration} min` : '—';
  const actionLabel = isLocked ? 'Unlock' : enrollment ? 'Start' : 'Preview';

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
              ${isLocked ? '<span class="lesson-card__lock">🔒 Locked</span>' : ''}
            </div>
          </div>
        </div>
        <button
          class="btn ${isLocked ? 'btn--secondary' : 'btn--primary'} btn--sm"
          data-lesson-index="${index}"
          data-lesson-locked="${isLocked}"
          aria-label="${isLocked ? 'Unlock lesson' : 'Start lesson'}: ${escapeHtml(lesson.title)}"
          ${isEnrolling ? 'disabled' : ''}
        >
          ${actionLabel}
        </button>
      </div>
    </div>
  `;

  const startBtn = div.querySelector('button');
  startBtn.addEventListener('click', () => {
    // Enroll request in flight — enrollment state is stale, so don't open a
    // lesson (it would render as an ungraded preview even when enrolled).
    if (isEnrolling) return;
    if (isLocked) {
      handleSubscribe();
      return;
    }
    openLessonViewer(lesson, index);
  });

  return div;
}

/**
 * Disable or re-enable every lesson row button while an enroll request is in
 * flight, so a lesson can't be opened against stale enrollment state (e.g. an
 * ungraded preview quiz while the student is actually enrolled).
 */
function setLessonButtonsDisabled(disabled) {
  lessonsList.querySelectorAll('[data-lesson-index]').forEach(btn => {
    btn.disabled = disabled;
  });
}

// ============================================================
// Lesson Viewer (adapted from index.html)
// ============================================================
function openLessonViewer(lesson, index) {
  // Build steps. The quiz answer key is never fetched here, it only comes back
  // from the quiz submission, so an unenrolled student sees an ungraded preview.
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

  if (!enrollment?.id) return;

  const answeredLesson = lessonState.lessonId;
  const answeredStep = lessonState.idx;

  // Enrolled students post the answer; the server grades it and is the only
  // source of the correct index and feedback.
  submitQuiz(answeredLesson, i)
    .then((response) => {
      const result = response?.data?.result;
      if (!result || !lessonOverlay.classList.contains('active')) return;
      if (lessonState.lessonId !== answeredLesson || lessonState.idx !== answeredStep) return;
      lessonState.isGraded = true;
      lessonState.correctIndex = result.correct_index;
      lessonState.quizFeedback = result.feedback || '';
      renderLessonStep();
    })
    .catch((err) => {
      if (!isNetworkError(err)) {
        showToast(safeErrorMessage(err), 'error');
      }
    });
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
      renderLessons();
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

  // Certificate button
  if (certBtn) {
    certBtn.addEventListener('click', async () => {
      try {
        const res = await issueCertificate(course.id);
        if (res.success) {
          renderCertificate(res.data);
        } else if (res.error && res.error.blockers) {
          showToast(`${res.error.message} ${res.error.blockers.join(' ')}`, 'error');
        }
      } catch (e) {
        showToast('Could not claim certificate. Please try again.', 'error');
      }
    });
  }

  // Subscribe button
  subscribeBtn.addEventListener('click', handleSubscribe);

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