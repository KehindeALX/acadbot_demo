/**
 * MSA AcadBot — Shared API Wrapper
 *
 * Handles Django session-based auth with CSRF protection.
 * All pages import this module for consistent API calls.
 *
 * CSRF FLOW (critical — Django SESSION cookies, not tokens):
 * 1. Before any POST/PATCH/DELETE, call getCsrfToken() first
 * 2. It GETs /api/auth/csrf/ → returns {"csrfToken": "..."}
 * 3. Store token in memory (module variable, NOT localStorage)
 * 4. Send as X-CSRFToken header on all mutating requests
 * 5. Every fetch MUST include credentials: 'include' for session cookies
 */

// ============================================================
// Configuration
// ============================================================
// TODO: Update for deployed backend URL during integration phase
const API_BASE = 'http://localhost:8000';

// In-memory CSRF token (never persisted to localStorage)
let csrfToken = null;

// Track if we're currently refreshing the token to avoid race conditions
let csrfRefreshPromise = null;

// ============================================================
// Core Fetch Wrapper
// ============================================================

/**
 * Internal fetch wrapper with consistent error handling
 * @param {string} endpoint - API endpoint (e.g., '/api/courses/')
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<any>} Parsed JSON response
 */
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  // Merge headers
  const headers = {
    ...defaultHeaders,
    ...options.headers,
  };

  // Add CSRF token for mutating requests
  const method = (options.method || 'GET').toUpperCase();
  if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(method)) {
    // Ensure we have a CSRF token
    await ensureCsrfToken();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
  }

  const config = {
    ...options,
    method,
    headers,
    credentials: 'include', // CRITICAL: Send/receive session cookies
  };

  try {
    const response = await fetch(url, config);

    // Handle 401/403 — session expired or not authenticated
    if (response.status === 401 || response.status === 403) {
      // Clear CSRF token so it's refreshed on next attempt
      csrfToken = null;
      // Don't redirect here — let the calling page decide
      // but we can throw a special error for the caller to catch
      const error = new Error('Authentication required');
      error.status = response.status;
      error.isAuthError = true;
      throw error;
    }

    // Parse JSON response
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    // Handle non-OK responses
    if (!response.ok) {
      // The backend wraps errors as { success: false, error: { code, message, details } }.
      // Prefer the nested error.message (the real shape), but keep the flat
      // data?.message / data?.detail as fallbacks for any unwrapped responses.
      const error = new Error(
        data?.error?.message || data?.message || data?.detail || 'Request failed'
      );
      error.status = response.status;
      error.data = data;
      error.details = data?.error?.details || null;
      throw error;
    }

    return data;
  } catch (err) {
    // Network errors or our thrown errors
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      const networkError = new Error('Network error. Please check your connection.');
      networkError.isNetworkError = true;
      networkError.originalError = err;
      throw networkError;
    }
    throw err;
  }
}

// ============================================================
// CSRF Token Management
// ============================================================

/**
 * Ensure we have a valid CSRF token, fetching if necessary.
 * Uses a promise to avoid multiple simultaneous fetches.
 */
async function ensureCsrfToken() {
  if (csrfToken) return;

  // If a refresh is already in flight, wait for it
  if (csrfRefreshPromise) {
    await csrfRefreshPromise;
    return;
  }

  csrfRefreshPromise = (async () => {
    try {
      const data = await fetch(`${API_BASE}/api/auth/csrf/`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
        },
      }).then(r => r.json());

      csrfToken = data.csrfToken || null;
    } catch (err) {
      console.warn('Failed to fetch CSRF token:', err);
      csrfToken = null;
    } finally {
      csrfRefreshPromise = null;
    }
  })();

  await csrfRefreshPromise;
}

/**
 * Force refresh the CSRF token (call after login/logout)
 */
async function refreshCsrfToken() {
  csrfToken = null;
  csrfRefreshPromise = null;
  await ensureCsrfToken();
}

/**
 * Clear the CSRF token (call on logout)
 */
function clearCsrfToken() {
  csrfToken = null;
  csrfRefreshPromise = null;
}

// ============================================================
// Auth API
// ============================================================

/**
 * Register a new user
 * @param {Object} payload - Registration data
 * @param {string} payload.username
 * @param {string} payload.email
 * @param {string} payload.password
 * @param {string} payload.password_confirm
 * @param {string} [payload.role='STUDENT']
 * @param {string} [payload.first_name]
 * @param {string} [payload.last_name]
 * @param {string} [payload.phone]
 * @returns {Promise<Object>} { success, message, data: { user } }
 */
export async function register(payload) {
  return apiFetch('/api/auth/register/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Log in a user
 * @param {Object} payload - Login credentials
 * @param {string} payload.email
 * @param {string} payload.password
 * @returns {Promise<Object>} { success, message, data: { user } }
 */
export async function login(payload) {
  const data = await apiFetch('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  // Refresh CSRF token after successful login
  await refreshCsrfToken();
  return data;
}

/**
 * Log out the current user
 * @returns {Promise<Object>} { success, message }
 */
export async function logout() {
  try {
    const data = await apiFetch('/api/auth/logout/', {
      method: 'POST',
    });
    clearCsrfToken();
    return data;
  } catch (err) {
    // Even if logout fails on server, clear local token
    clearCsrfToken();
    throw err;
  }
}

/**
 * Get current authenticated user
 * @returns {Promise<Object>} { success, data: { user } }
 */
export async function getMe() {
  return apiFetch('/api/auth/me/', {
    method: 'GET',
  });
}

// ============================================================
// Courses API
// ============================================================

/**
 * List all published courses (paginated)
 * @param {Object} [params] - Query parameters
 * @param {number} [params.page] - Page number
 * @param {string} [params.career] - Filter by career slug
 * @returns {Promise<Object>} { count, next, previous, results: Course[] }
 */
export async function listCourses(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set('page', params.page);
  if (params.career) searchParams.set('career', params.career);

  const query = searchParams.toString();
  return apiFetch(`/api/courses/${query ? `?${query}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Get a single course by ID (includes lessons)
 * @param {string|number} id - Course ID
 * @returns {Promise<Object>} Course with lessons array
 */
export async function getCourse(id) {
  return apiFetch(`/api/courses/${id}/`, {
    method: 'GET',
  });
}

/**
 * Enroll in a course
 * @param {string|number} courseId - Course ID
 * @returns {Promise<Object>} { success, message, data: { enrollment } }
 */
export async function enrollCourse(courseId) {
  return apiFetch(`/api/courses/${courseId}/enroll/`, {
    method: 'POST',
    body: JSON.stringify({}), // Empty body, course ID in URL
  });
}

/**
 * List current user's enrollments (paginated)
 * @param {Object} [params] - Query parameters
 * @param {number} [params.page] - Page number
 * @returns {Promise<Object>} { count, next, previous, results: Enrollment[] }
 */
export async function listEnrollments(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set('page', params.page);

  const query = searchParams.toString();
  return apiFetch(`/api/courses/enrollments/${query ? `?${query}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Get one enrollment's detailed progress (includes per-lesson progress).
 * @param {string|number} enrollmentId - Enrollment ID
 * @returns {Promise<Object>} { success, data: { id, progress_percent, lesson_progress: [...] } }
 */
export async function getEnrollmentDetail(enrollmentId) {
  return apiFetch(`/api/courses/enrollments/${enrollmentId}/`, {
    method: 'GET',
  });
}

/**
 * Get a single lesson's full detail — includes the quiz answer key and
 * feedback, which the course-detail list deliberately omits.
 * @param {string|number} lessonId - Lesson ID
 * @returns {Promise<Object>} Lesson with quiz_correct_index, quiz_feedback
 */
export async function getLessonDetail(lessonId) {
  return apiFetch(`/api/courses/lessons/${lessonId}/`, {
    method: 'GET',
  });
}

/**
 * Mark a lesson complete for the enrolled student.
 * @param {string|number} lessonId - Lesson ID
 * @returns {Promise<Object>} { success, message, data: LessonProgress }
 */
export async function completeLesson(lessonId) {
  return apiFetch(`/api/courses/lessons/${lessonId}/complete/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

/**
 * Submit a quiz answer for a lesson. Only meaningful once enrolled.
 * @param {string|number} lessonId - Lesson ID
 * @param {number} answerIndex - Index of the chosen option
 * @returns {Promise<Object>} { success, message, data: { progress, result } }
 */
export async function submitQuiz(lessonId, answerIndex) {
  return apiFetch(`/api/courses/lessons/${lessonId}/quiz/`, {
    method: 'POST',
    body: JSON.stringify({ answer_index: answerIndex }),
  });
}

// ============================================================
// Careers API — MSA AI Guide
// ============================================================

/**
 * List all published career paths (paginated)
 * @param {Object} [params] - Query parameters
 * @param {number} [params.page] - Page number
 * @returns {Promise<Object>} { count, next, previous, results: Career[] }
 */
export async function listCareers(params = {}) {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set('page', params.page);

  const query = searchParams.toString();
  return apiFetch(`/api/careers/${query ? `?${query}` : ''}`, {
    method: 'GET',
  });
}

/**
 * Get a single career by slug (includes skills, roadmap, questions)
 * @param {string} slug - Career slug (e.g. 'data', 'cyber', 'software')
 * @returns {Promise<Object>} Career with skills[], roadmap_stages[], interview_questions[]
 */
export async function getCareer(slug) {
  return apiFetch(`/api/careers/${slug}/`, {
    method: 'GET',
  });
}

// ============================================================
// Chat API — Ask AcadBot
// ============================================================

/**
 * Send a message to the AcadBot AI assistant.
 *
 * INTEGRATION NOTE: No chat/AI endpoint is routed on the backend yet
 * (PRODUCT.md principle #2 — no invented endpoints), so this returns a
 * "not connected" placeholder rather than calling a fabricated URL.
 *
 * At integration time, replace this body with the real call, e.g.:
 *   return apiFetch('/api/chat/', {
 *     method: 'POST',
 *     body: JSON.stringify({ message }),
 *   });
 * and adjust the response shape to match the backend serializer.
 *
 * @param {Object} payload
 * @param {string} payload.message - The user's message to AcadBot
 * @returns {Promise<Object>}
 */
export async function askAcadBot(payload) {
  // TODO(integration): wire to the real chat endpoint when routed.
  // Deliberately NOT faked and NOT pointed at an invented URL.
  return {
    success: true,
    message: 'AcadBot is not connected yet — your message was received.',
    data: { acknowledged: true },
  };
}

// ============================================================
// Chat API — Guide Abia (MSA AI Guide)
// ============================================================

/**
 * Send a message to the Abia AI career guide.
 *
 * INTEGRATION NOTE: No chat/AI endpoint is routed on the backend yet
 * (PRODUCT.md principle #2 — no invented endpoints), so this returns a
 * "not connected" placeholder rather than calling a fabricated URL.
 *
 * At integration time, replace this body with the real call, e.g.:
 *   return apiFetch('/api/careers/chat/', {
 *     method: 'POST',
 *     body: JSON.stringify({ career_slug, message }),
 *   });
 *
 * @param {Object} payload
 * @param {string} payload.message - The user's message to Abia
 * @param {string} [payload.career_slug] - Active career slug for context
 * @returns {Promise<Object>}
 */
export async function guideAbia(payload) {
  // TODO(integration): wire to the real chat endpoint when routed.
  // Deliberately NOT faked and NOT pointed at an invented URL.
  return {
    success: true,
    message: 'Abia is not connected yet — your message was received. The career guide AI will respond here once it\'s wired to the backend.',
    data: { acknowledged: true },
  };
}

// ============================================================
// Error Handling Helpers
// ============================================================

/**
 * Format API error for user display
 * @param {Error} error - Error thrown by apiFetch
 * @returns {string} User-friendly error message
 */
export function formatApiError(error) {
  if (error.isNetworkError) {
    return 'Unable to connect to the server. Please check your internet connection and try again.';
  }

  if (error.isAuthError) {
    return 'Your session has expired. Please log in again.';
  }

  // Field-level validation errors. apiFetch sets error.details to the backend's
  // nested { field: ['message'] } dict (data.error.details) — iterate that, not
  // error.data, which is the full { success, error } envelope.
  if (error.details && typeof error.details === 'object') {
    const messages = [];

    // Field-specific errors
    for (const [field, fieldErrors] of Object.entries(error.details)) {
      if (Array.isArray(fieldErrors)) {
        fieldErrors.forEach(msg => {
          const fieldName = field === 'non_field_errors' ? '' : `${field}: `;
          messages.push(`${fieldName}${msg}`);
        });
      } else if (typeof fieldErrors === 'string') {
        const fieldName = field === 'non_field_errors' ? '' : `${field}: `;
        messages.push(`${fieldName}${fieldErrors}`);
      }
    }

    if (messages.length > 0) {
      return messages.join('\n');
    }
  }

  // Generic error message from the nested envelope
  if (error.data?.error?.message) {
    return error.data.error.message;
  }
  if (error.message) {
    return error.message;
  }

  return 'Something went wrong. Please try again.';
}

/**
 * Check if error is a validation error (400)
 * @param {Error} error
 * @returns {boolean}
 */
export function isValidationError(error) {
  return error.status === 400;
}

/**
 * Check if error is an auth error (401/403)
 * @param {Error} error
 * @returns {boolean}
 */
export function isAuthError(error) {
  return error.isAuthError === true || error.status === 401 || error.status === 403;
}

/**
 * Check if error is a network error
 * @param {Error} error
 * @returns {boolean}
 */
export function isNetworkError(error) {
  return error.isNetworkError === true;
}

// ============================================================
// Export all
// ============================================================

export const api = {
  // Config
  API_BASE,

  // Core
  fetch: apiFetch,

  // CSRF
  ensureCsrfToken,
  refreshCsrfToken,
  clearCsrfToken,

  // Auth
  register,
  login,
  logout,
  getMe,

  // Courses
  listCourses,
  getCourse,
  enrollCourse,
  listEnrollments,
  getEnrollmentDetail,
  getLessonDetail,
  completeLesson,
  submitQuiz,

  // Careers
  listCareers,
  getCareer,

  // Chat
  askAcadBot,
  guideAbia,

  // Error helpers
  formatApiError,
  isValidationError,
  isAuthError,
  isNetworkError,
};

export default api;