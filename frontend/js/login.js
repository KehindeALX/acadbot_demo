/**
 * MSA AcadBot — Login Page Logic
 */

import { login, getMe, formatApiError, isAuthError } from './api.js';

// ============================================================
// DOM Elements
// ============================================================
const form = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submitBtn');
const btnText = submitBtn.querySelector('.btn__text');
const btnLoading = submitBtn.querySelector('.btn__loading');
const formError = document.getElementById('formError');
const formErrorMessage = document.getElementById('formErrorMessage');
const emailError = document.getElementById('emailError');
const passwordError = document.getElementById('passwordError');
const toastContainer = document.getElementById('toastContainer');

// ============================================================
// State
// ============================================================
let isSubmitting = false;
let redirectTarget = 'dashboard.html';

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  // Read optional redirect target from URL (?redirect=...)
  const urlParams = new URLSearchParams(window.location.search);
  const redirect = urlParams.get('redirect');
  if (redirect && redirect.startsWith('.html')) {
    redirectTarget = redirect;
  }

  // Check if already logged in
  checkAuthState();

  // Event listeners
  form.addEventListener('submit', handleSubmit);
  emailInput.addEventListener('input', () => clearFieldError(emailInput, emailError));
  passwordInput.addEventListener('input', () => clearFieldError(passwordInput, passwordError));
  formError.querySelector('.alert__dismiss').addEventListener('click', () => hideFormError());
});

// ============================================================
// Auth State Check
// ============================================================
async function checkAuthState() {
  try {
    const data = await getMe();
    if (data.success && data.data) {
      // Already logged in, redirect
      window.location.href = redirectTarget;
    }
  } catch (err) {
    // Not logged in, stay on login page
    if (isAuthError(err)) {
      // Expected - not authenticated
      return;
    }
    // Network error - just stay on page
    console.warn('Auth check failed:', err);
  }
}

// ============================================================
// Form Submission
// ============================================================
async function handleSubmit(event) {
  event.preventDefault();

  if (isSubmitting) return;

  // Clear previous errors
  hideFormError();
  clearFieldError(emailInput, emailError);
  clearFieldError(passwordInput, passwordError);

  // Validate
  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email) {
    showFieldError(emailInput, emailError, 'Email is required');
    emailInput.focus();
    return;
  }

  if (!isValidEmail(email)) {
    showFieldError(emailInput, emailError, 'Please enter a valid email address');
    emailInput.focus();
    return;
  }

  if (!password) {
    showFieldError(passwordInput, passwordError, 'Password is required');
    passwordInput.focus();
    return;
  }

  // Submit
  setSubmitting(true);

  try {
    const data = await login({ email, password });

    if (data.success) {
      showToast('Welcome back!', 'success');
      // Redirect after brief delay
      setTimeout(() => {
        window.location.href = redirectTarget;
      }, 800);
    } else {
      showFormError(data.message || 'Login failed. Please try again.');
    }
  } catch (err) {
    if (isAuthError(err)) {
      showFormError('Your session has expired. Please log in again.');
    } else {
      // Bad credentials, disabled account, etc. — surface the real backend
      // message. UserLoginSerializer already returns "Invalid email or password."
      // on bad credentials, so formatApiError surfaces it correctly.
      showFormError(formatApiError(err));
    }
  } finally {
    setSubmitting(false);
  }
}

// ============================================================
// UI Helpers
// ============================================================
function setSubmitting(submitting) {
  isSubmitting = submitting;
  submitBtn.disabled = submitting;
  btnText.classList.toggle('hidden', submitting);
  btnLoading.classList.toggle('hidden', !submitting);
}

function showFieldError(input, errorEl, message) {
  input.setAttribute('aria-invalid', 'true');
  input.style.borderColor = 'var(--red)';
  errorEl.textContent = message;
  errorEl.classList.add('visible');
}

function clearFieldError(input, errorEl) {
  input.removeAttribute('aria-invalid');
  input.style.borderColor = '';
  errorEl.textContent = '';
  errorEl.classList.remove('visible');
}

function showFormError(message) {
  formErrorMessage.textContent = message;
  formError.classList.remove('hidden');
  // Scroll to error if needed
  formError.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function hideFormError() {
  formError.classList.add('hidden');
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <span class="toast__icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
    <div class="toast__content">
      <div class="toast__message">${message}</div>
    </div>
  `;

  toastContainer.appendChild(toast);

  // Auto-dismiss after 4 seconds
  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function isValidEmail(email) {
  // Simple but effective email validation
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}