/**
 * MSA AcadBot — Courses Page Logic
 * Lists all published courses with career filtering and pagination
 */

import {
  listCourses,
  listCareers,
  getMe,
  formatApiError,
  isAuthError,
  isNetworkError
} from './api.js';

// ============================================================
// DOM Elements
// ============================================================
const coursesGrid = document.getElementById('coursesGrid');
const careerFilters = document.getElementById('careerFilters');
const loadingState = document.getElementById('loadingState');
const emptyState = document.getElementById('emptyState');
const clearFilterBtn = document.getElementById('clearFilterBtn');
const pagination = document.getElementById('pagination');
const authNav = document.getElementById('authNav');
const toastContainer = document.getElementById('toastContainer');

// ============================================================
// State
// ============================================================
let currentPage = 1;
let currentCareerFilter = '';
let allCourses = [];
let allCareers = [];
let isLoading = false;
let user = null;

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  await checkAuthState();

  // Restore a shared/direct-linked filter from the URL (?career=slug)
  const careerParam = new URLSearchParams(window.location.search).get('career');
  if (careerParam) {
    currentCareerFilter = careerParam;
  }

  await loadCareerFilters();
  await loadCourses();
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
      // Not logged in - that's fine for courses page
      renderAuthNav();
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
  // Import logout dynamically to avoid circular deps
  const { logout } = await import('./api.js');
  try {
    await logout();
    user = null;
    renderAuthNav();
    showToast('Logged out successfully', 'success');
  } catch (err) {
    showToast('Logout failed', 'error');
  }
}

// ============================================================
// Load Courses
// ============================================================
async function loadCourses(page = 1) {
  if (isLoading) return;
  isLoading = true;
  currentPage = page;

  showLoading(true);
  hideEmptyState();

  try {
    const params = { page };
    if (currentCareerFilter) {
      params.career = currentCareerFilter;
    }

    const data = await listCourses(params);

    if (data.results) {
      allCourses = data.results;
      renderCourses();
      renderPagination(data.count, data.next, data.previous);
    } else {
      allCourses = [];
      renderCourses();
    }
  } catch (err) {
    const message = formatApiError(err);
    showToast(message, 'error');
    renderCourses(); // Will show empty state
  } finally {
    showLoading(false);
    isLoading = false;
  }
}

async function loadCareerFilters() {
  // Career chips come from the real /api/careers/ endpoint (correct and
  // complete regardless of the active course filter).
  try {
    const data = await listCareers();
    allCareers = (data.results || []).map(c => ({ slug: c.slug, name: c.name }));
  } catch (err) {
    // If the careers endpoint is unavailable, fall back to whatever courses
    // the first page already returned so the filter still renders.
    allCareers = extractCareers(allCourses);
    if (!isNetworkError(err)) {
      showToast(formatApiError(err), 'error');
    }
  }
  renderCareerFilters();
}

function extractCareers(courses) {
  const careerMap = new Map();
  courses.forEach(course => {
    if (course.career && course.career.slug && course.career.name) {
      careerMap.set(course.career.slug, course.career.name);
    }
  });
  return Array.from(careerMap.entries()).map(([slug, name]) => ({ slug, name }));
}

// ============================================================
// Render Functions
// ============================================================
function renderCourses() {
  coursesGrid.innerHTML = '';

  if (allCourses.length === 0) {
    showEmptyState();
    return;
  }

  hideEmptyState();

  allCourses.forEach(course => {
    const card = createCourseCard(course);
    coursesGrid.appendChild(card);
  });
}

function createCourseCard(course) {
  const card = document.createElement('article');
  card.className = 'course-card';
  card.setAttribute('role', 'listitem');

  const careerName = course.career?.name || 'General';
  const careerSlug = course.career?.slug || '';
  const lessonsCount = course.lessons_count || 0;
  const totalDuration = course.total_duration_minutes || 0;
  const durationHours = Math.floor(totalDuration / 60);
  const durationMins = totalDuration % 60;
  const durationStr = durationHours > 0
    ? `${durationHours}h ${durationMins}m`
    : `${durationMins}m`;

  // Thumbnail or placeholder
  let thumbnailHtml;
  if (course.thumbnail) {
    thumbnailHtml = `<img src="${course.thumbnail}" alt="" class="course-card__thumbnail" loading="lazy"/>`;
  } else {
    // Career-specific icons as placeholder
    const careerIcons = {
      'data': '📊',
      'cyber': '🔐',
      'software': '💻',
      'ai': '🤖',
      'uiux': '🎨',
      'product': '🗺️',
      'digital': '📱',
      'cloud': '☁️',
    };
    const icon = careerIcons[careerSlug] || '📚';
    thumbnailHtml = `<div class="course-card__placeholder">${icon}</div>`;
  }

  card.innerHTML = `
    ${thumbnailHtml}
    <div class="course-card__content">
      <span class="course-card__career">${careerName}</span>
      <h3 class="course-card__title">${escapeHtml(course.title)}</h3>
      <p class="course-card__description">${escapeHtml(course.description || 'No description available.')}</p>
      <div class="course-card__meta">
        <span class="course-card__meta-item">
          <span>📖</span> ${lessonsCount} lesson${lessonsCount !== 1 ? 's' : ''}
        </span>
        <span class="course-card__meta-item">
          <span>⏱</span> ${durationStr}
        </span>
        <span class="course-card__meta-item">
          <span>📦</span> Module ${course.module_number || 1}
        </span>
      </div>
      <a href="course-detail.html?id=${course.id}" class="btn btn--primary btn--block">
        View Course
      </a>
    </div>
  `;

  return card;
}

function renderCareerFilters() {
  // Keep the "All Careers" button
  const allBtn = careerFilters.querySelector('[data-career=""]');
  careerFilters.innerHTML = '';
  careerFilters.appendChild(allBtn);

  allCareers.forEach(career => {
    const btn = document.createElement('button');
    btn.className = 'btn btn--secondary';
    btn.setAttribute('aria-pressed', 'false');
    btn.setAttribute('data-career', career.slug);
    btn.textContent = career.name;
    careerFilters.appendChild(btn);
  });

  // Mark whichever filter is active (restored from the URL, if any)
  setActiveFilter(currentCareerFilter);

  // Re-attach click handlers
  careerFilters.querySelectorAll('[data-career]').forEach(btn => {
    btn.addEventListener('click', () => handleCareerFilter(btn.dataset.career));
  });
}

// Single-select semantics: exactly one chip is active at a time.
function setActiveFilter(careerSlug) {
  careerFilters.querySelectorAll('[data-career]').forEach(btn => {
    const isActive = btn.dataset.career === careerSlug;
    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    btn.classList.toggle('btn--primary', isActive);
    btn.classList.toggle('btn--secondary', !isActive);
  });
}

function renderPagination(totalCount, nextUrl, prevUrl) {
  pagination.innerHTML = '';

  if (!nextUrl && !prevUrl) {
    pagination.classList.add('hidden');
    return;
  }

  pagination.classList.remove('hidden');

  // Previous button
  if (prevUrl) {
    const prevBtn = document.createElement('a');
    prevBtn.className = 'pagination__link';
    prevBtn.href = '#';
    prevBtn.textContent = '← Previous';
    prevBtn.dataset.page = currentPage - 1;
    prevBtn.addEventListener('click', (e) => {
      e.preventDefault();
      loadCourses(currentPage - 1);
    });
    pagination.appendChild(prevBtn);
  }

  // Page info
  const pageInfo = document.createElement('span');
  pageInfo.className = 'pagination__info';
  pageInfo.style.cssText = 'color: var(--muted); font-size: 13px; padding: 0 var(--space-md);';
  const start = (currentPage - 1) * 20 + 1;
  const end = Math.min(currentPage * 20, totalCount);
  pageInfo.textContent = `Showing ${start}–${end} of ${totalCount}`;
  pagination.appendChild(pageInfo);

  // Next button
  if (nextUrl) {
    const nextBtn = document.createElement('a');
    nextBtn.className = 'pagination__link';
    nextBtn.href = '#';
    nextBtn.textContent = 'Next →';
    nextBtn.dataset.page = currentPage + 1;
    nextBtn.addEventListener('click', (e) => {
      e.preventDefault();
      loadCourses(currentPage + 1);
    });
    pagination.appendChild(nextBtn);
  }
}

function showLoading(show) {
  loadingState.classList.toggle('hidden', !show);
  coursesGrid.classList.toggle('hidden', show);
}

function showEmptyState() {
  emptyState.classList.remove('hidden');
  coursesGrid.classList.add('hidden');
  pagination.classList.add('hidden');
}

function hideEmptyState() {
  emptyState.classList.add('hidden');
  coursesGrid.classList.remove('hidden');
}

// ============================================================
// Event Handlers
// ============================================================
function handleCareerFilter(careerSlug) {
  if (careerSlug === currentCareerFilter) return; // already active — no round-trip

  currentCareerFilter = careerSlug;
  setActiveFilter(careerSlug);

  // Keep the filter shareable and preserved across reloads, without a page nav.
  const url = new URL(window.location.href);
  if (careerSlug) {
    url.searchParams.set('career', careerSlug);
  } else {
    url.searchParams.delete('career');
  }
  window.history.replaceState({}, '', url);

  loadCourses(1); // Reset to first page
}

function setupEventListeners() {
  clearFilterBtn.addEventListener('click', () => {
    handleCareerFilter('');
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