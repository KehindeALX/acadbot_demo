/**
 * MSA AcadBot — Dashboard Page Logic
 * Requires authentication. Shows the logged-in user's enrollments.
 * Redirects to login.html if not authenticated.
 */

import {
  getMe,
  listEnrollments,
  formatApiError,
  isAuthError,
  isNetworkError
} from './api.js';

// ============================================================
// DOM Elements
// ============================================================
const dashboardUserName = document.getElementById('dashboardUserName');
const statsGrid = document.getElementById('statsGrid');
const enrollmentsLoading = document.getElementById('enrollmentsLoading');
const enrollmentsList = document.getElementById('enrollmentsList');
const emptyState = document.getElementById('emptyState');
const pagination = document.getElementById('pagination');
const authNav = document.getElementById('authNav');
const toastContainer = document.getElementById('toastContainer');

// ============================================================
// State
// ============================================================
let user = null;
let enrollments = [];
let currentPage = 1;
let isLoading = false;

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  const authenticated = await requireAuth();
  if (!authenticated) return; // Redirected to login

  setupEventListeners();
  await loadEnrollments(1);
});

// ============================================================
// Auth Guard
// ============================================================
async function requireAuth() {
  try {
    const data = await getMe();
    if (data.success && data.data) {
      user = data.data;
      renderUser();
      return true;
    }
    // Unexpected: no user in response but no error
    redirectToLogin();
    return false;
  } catch (err) {
    if (isAuthError(err)) {
      redirectToLogin();
      return false;
    }
    if (isNetworkError(err)) {
      showToast('Unable to connect to the server. Please check your connection.', 'error');
      return false;
    }
    showToast('Something went wrong loading your account. Please try again.', 'error');
    return false;
  }
}

function redirectToLogin() {
  // Preserve current page as redirect target
  window.location.href = 'login.html';
}

// ============================================================
// Render User
// ============================================================
function renderUser() {
  if (!user) return;

  const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;
  dashboardUserName.textContent = `, ${displayName}`;

  authNav.innerHTML = `
    <span class="navbar__user-name">${displayName}</span>
    <a href="dashboard.html" class="navbar__link">Dashboard</a>
    <button id="logoutBtn" class="navbar__btn">Logout</button>
  `;
  document.getElementById('logoutBtn').addEventListener('click', handleLogout);
}

async function handleLogout() {
  const { logout } = await import('./api.js');
  try {
    await logout();
    window.location.href = 'login.html';
  } catch (err) {
    showToast('Logout failed', 'error');
  }
}

// ============================================================
// Load Enrollments
// ============================================================
async function loadEnrollments(page = 1) {
  if (isLoading) return;
  isLoading = true;
  currentPage = page;

  enrollmentsLoading.classList.remove('hidden');
  enrollmentsList.classList.add('hidden');
  emptyState.classList.add('hidden');
  statsGrid.innerHTML = '';
  pagination.classList.add('hidden');

  try {
    const data = await listEnrollments({ page });

    enrollments = data.results || [];
    renderStats(data.count || enrollments.length);
    renderEnrollments();
    renderPagination(data.count || 0, data.next, data.previous);

    if (enrollments.length === 0) {
      emptyState.classList.remove('hidden');
    } else {
      enrollmentsList.classList.remove('hidden');
    }
  } catch (err) {
    const message = formatApiError(err);
    showToast(message, 'error');
    enrollmentsList.classList.remove('hidden');
    renderEnrollments(); // Will show empty
  } finally {
    enrollmentsLoading.classList.add('hidden');
    isLoading = false;
  }
}

// ============================================================
// Stats
// ============================================================
function renderStats(totalEnrollments) {
  const activeCount = enrollments.filter(e => e.status === 'ACTIVE').length;
  const completedCount = enrollments.filter(e => e.status === 'COMPLETED').length;
  const inProgressCount = enrollments.filter(e => e.progress_percent > 0 && e.progress_percent < 100).length;

  const stats = [
    {
      icon: '📚',
      label: 'Total Enrollments',
      value: totalEnrollments,
      color: 'var(--gold)'
    },
    {
      icon: '🚀',
      label: 'In Progress',
      value: inProgressCount,
      color: 'var(--teal)'
    },
    {
      icon: '🏆',
      label: 'Completed',
      value: completedCount,
      color: 'var(--green)'
    }
  ];

  statsGrid.innerHTML = stats.map(stat => `
    <div class="card">
      <div class="card__body stat-card__body">
        <div class="stat-card__icon">${stat.icon}</div>
        <div class="stat-card__value" style="color: ${stat.color};">${stat.value}</div>
        <div class="stat-card__label">${stat.label}</div>
      </div>
    </div>
  `).join('');
}

// ============================================================
// Render Enrollments
// ============================================================
function renderEnrollments() {
  enrollmentsList.innerHTML = '';

  if (enrollments.length === 0) {
    return;
  }

  enrollments.forEach(enrollment => {
    const card = createEnrollmentCard(enrollment);
    enrollmentsList.appendChild(card);
  });
}

function createEnrollmentCard(enrollment) {
  const course = enrollment.course || {};
  const progress = enrollment.progress_percent || 0;
  const status = enrollment.status || 'ACTIVE';

  const statusLabels = {
    ACTIVE: 'In Progress',
    COMPLETED: 'Completed',
    DROPPED: 'Dropped',
    PENDING: 'Pending',
  };

  const statusBadges = {
    ACTIVE: 'card__badge--active',
    COMPLETED: 'card__badge--completed',
    DROPPED: 'card__badge--draft',
    PENDING: 'card__badge--draft',
  };

  const statusLabel = statusLabels[status] || status;
  const statusBadgeClass = statusBadges[status] || 'card__badge--draft';

  const careerName = course.career?.name || 'General';
  const lessonsCount = course.lessons_count || 0;
  const totalDuration = course.total_duration_minutes || 0;
  const durationHours = Math.floor(totalDuration / 60);
  const durationMins = totalDuration % 60;
  const durationStr = durationHours > 0
    ? `${durationHours}h ${durationMins}m`
    : `${durationMins}m`;

  const enrolledDate = formatDate(enrollment.enrolled_at);

  const card = document.createElement('article');
  card.className = 'card enrollment-card';

  card.innerHTML = `
    <div class="card__body">
      <div class="enrollment-card__header">
        <div>
          <span class="course-card__career">${escapeHtml(careerName)}</span>
          <h3 class="card__title enrollment-card__title">
            ${escapeHtml(course.title || 'Untitled Course')}
          </h3>
        </div>
        <span class="card__badge ${statusBadgeClass}">${statusLabel}</span>
      </div>

      <div class="enrollment-card__meta">
        <span>📖 ${lessonsCount} lessons</span>
        <span>⏱ ${durationStr}</span>
        <span>📅 Enrolled ${enrolledDate}</span>
      </div>

      <div class="enrollment-card__progress-wrap">
        <div class="enrollment-card__progress-row">
          <span>Progress</span>
          <span id="progressLabel-${enrollment.id}" class="enrollment-card__progress-value">${progress}%</span>
        </div>
        <div class="progress" role="progressbar" aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100" aria-label="Course progress">
          <div class="progress__bar" id="progressBar-${enrollment.id}" style="width: ${progress}%;"></div>
        </div>
      </div>

      <div class="enrollment-card__actions">
        <a href="course-detail.html?id=${course.id}" class="btn btn--primary btn--sm">${status === 'COMPLETED' ? 'Review' : 'Continue'}</a>
        <a href="courses.html" class="btn btn--ghost btn--sm">Browse More Courses</a>
      </div>
    </div>
  `;

  return card;
}

// ============================================================
// Pagination
// ============================================================
function renderPagination(totalCount, nextUrl, prevUrl) {
  pagination.innerHTML = '';

  if (!nextUrl && !prevUrl) {
    pagination.classList.add('hidden');
    return;
  }

  pagination.classList.remove('hidden');

  if (prevUrl) {
    const prevBtn = document.createElement('a');
    prevBtn.className = 'pagination__link';
    prevBtn.href = '#';
    prevBtn.textContent = '← Previous';
    prevBtn.addEventListener('click', (e) => {
      e.preventDefault();
      loadEnrollments(currentPage - 1);
    });
    pagination.appendChild(prevBtn);
  }

  const pageInfo = document.createElement('span');
  pageInfo.style.cssText = 'color: var(--muted); font-size: 13px; padding: 0 var(--space-md);';
  const start = (currentPage - 1) * 20 + 1;
  const end = Math.min(currentPage * 20, totalCount);
  pageInfo.textContent = `Showing ${start}–${end} of ${totalCount}`;
  pagination.appendChild(pageInfo);

  if (nextUrl) {
    const nextBtn = document.createElement('a');
    nextBtn.className = 'pagination__link';
    nextBtn.href = '#';
    nextBtn.textContent = 'Next →';
    nextBtn.addEventListener('click', (e) => {
      e.preventDefault();
      loadEnrollments(currentPage + 1);
    });
    pagination.appendChild(nextBtn);
  }
}

// ============================================================
// Event Listeners
// ============================================================
function setupEventListeners() {
  // Nothing to set up globally; handlers are attached in render functions
}

// ============================================================
// Utilities
// ============================================================
function formatDate(dateString) {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

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