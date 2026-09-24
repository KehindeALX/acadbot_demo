/**
 * MSA AcadBot — Register Page Logic
 */

import { register, getMe, safeErrorMessage, isAuthError } from './api.js';

// ============================================================
// DOM Elements
// ============================================================
const form = document.getElementById('registerForm');
const firstNameInput = document.getElementById('first_name');
const lastNameInput = document.getElementById('last_name');
const emailInput = document.getElementById('email');
const usernameInput = document.getElementById('username');
const phoneInput = document.getElementById('phone');
const passwordInput = document.getElementById('password');
const passwordConfirmInput = document.getElementById('password_confirm');
const submitBtn = document.getElementById('submitBtn');
const btnText = submitBtn.querySelector('.btn__text');
const btnLoading = submitBtn.querySelector('.btn__loading');
const formError = document.getElementById('formError');
const formErrorMessage = document.getElementById('formErrorMessage');
const firstNameError = document.getElementById('firstNameError');
const lastNameError = document.getElementById('lastNameError');
const emailError = document.getElementById('emailError');
const usernameError = document.getElementById('usernameError');
const phoneError = document.getElementById('phoneError');
const passwordError = document.getElementById('passwordError');
const passwordConfirmError = document.getElementById('passwordConfirmError');
const toastContainer = document.getElementById('toastContainer');

// Password toggle & strength elements
const passwordToggle = document.getElementById('passwordToggle');
const passwordEyeOpen = document.getElementById('eyeOpen');
const passwordEyeClosed = document.getElementById('eyeClosed');
const passwordConfirmToggle = document.getElementById('passwordConfirmToggle');
const passwordConfirmEyeOpen = passwordConfirmToggle.querySelector('.eye-open-confirm');
const passwordConfirmEyeClosed = passwordConfirmToggle.querySelector('.eye-closed-confirm');
const passwordStrength = document.getElementById('passwordStrength');
const strengthBar = document.getElementById('strengthBar');
const passwordStrengthCount = document.getElementById('passwordStrengthCount');
const strengthRules = document.querySelectorAll('#strengthRules .password-strength__rule');

// ============================================================
// State
// ============================================================
let isSubmitting = false;

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  // Check if already logged in
  checkAuthState();

  // Event listeners
  form.addEventListener('submit', handleSubmit);

  // Clear field errors on input
  firstNameInput.addEventListener('input', () => clearFieldError(firstNameInput, firstNameError));
  lastNameInput.addEventListener('input', () => clearFieldError(lastNameInput, lastNameError));
  emailInput.addEventListener('input', () => clearFieldError(emailInput, emailError));
  usernameInput.addEventListener('input', () => clearFieldError(usernameInput, usernameError));
  phoneInput.addEventListener('input', () => clearFieldError(phoneInput, phoneError));
  passwordInput.addEventListener('input', () => {
    clearFieldError(passwordInput, passwordError);
    updatePasswordStrength(passwordInput.value);
    // Also validate confirm if it has a value
    if (passwordConfirmInput.value) {
      validatePasswordMatch();
    }
  });
  passwordConfirmInput.addEventListener('input', validatePasswordMatch);

  // Password toggle buttons
  passwordToggle.addEventListener('click', () => togglePasswordVisibility(passwordInput, passwordEyeOpen, passwordEyeClosed));
  passwordConfirmToggle.addEventListener('click', () => togglePasswordVisibility(passwordConfirmInput, passwordConfirmEyeOpen, passwordConfirmEyeClosed));

  formError.querySelector('.alert__dismiss').addEventListener('click', () => hideFormError());
});

// ============================================================
// Auth State Check
// ============================================================
async function checkAuthState() {
  try {
    const data = await getMe();
    if (data.success && data.data) {
      // Already logged in, redirect to dashboard
      window.location.href = 'dashboard.html';
    }
  } catch (err) {
    // Not logged in, stay on register page
    if (isAuthError(err)) {
      return;
    }
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
  clearAllFieldErrors();

  // Validate all fields
  const validation = validateForm();
  if (!validation.valid) {
    // Focus first invalid field
    const firstInvalid = form.querySelector('[aria-invalid="true"]');
    if (firstInvalid) firstInvalid.focus();
    return;
  }

  // Submit
  setSubmitting(true);

  try {
    const payload = {
      first_name: firstNameInput.value.trim(),
      last_name: lastNameInput.value.trim(),
      email: emailInput.value.trim().toLowerCase(),
      username: usernameInput.value.trim(),
      password: passwordInput.value,
      password_confirm: passwordConfirmInput.value,
      // role defaults to STUDENT on backend
    };

    // Only include phone if provided
    if (phoneInput.value.trim()) {
      payload.phone = phoneInput.value.trim();
    }

    const data = await register(payload);

    if (data.success) {
      showToast('Account created successfully! Redirecting...', 'success');
      setTimeout(() => {
        window.location.href = 'dashboard.html';
      }, 1000);
    } else {
      showFormError(data.message || 'Registration failed. Please try again.');
    }
  } catch (err) {
    // Field-level validation errors — show on each field (safe messages only)
    if (err.status === 400 && err.details) {
      handleValidationErrors(err.details);
    } else {
      // Network, server, or unexpected errors — never expose backend details
      showFormError(safeErrorMessage(err));
    }
  } finally {
    setSubmitting(false);
  }
}

// ============================================================
// Validation
// ============================================================
function validateForm() {
  let valid = true;

  // First name (optional but if provided, validate)
  if (firstNameInput.value.trim() && firstNameInput.value.trim().length < 1) {
    showFieldError(firstNameInput, firstNameError, 'First name is too short');
    valid = false;
  }

  // Last name (optional but if provided, validate)
  if (lastNameInput.value.trim() && lastNameInput.value.trim().length < 1) {
    showFieldError(lastNameInput, lastNameError, 'Last name is too short');
    valid = false;
  }

  // Email
  const email = emailInput.value.trim();
  if (!email) {
    showFieldError(emailInput, emailError, 'Email is required');
    valid = false;
  } else if (!isValidEmail(email)) {
    showFieldError(emailInput, emailError, 'Please enter a valid email address');
    valid = false;
  }

  // Username
  const username = usernameInput.value.trim();
  if (!username) {
    showFieldError(usernameInput, usernameError, 'Username is required');
    valid = false;
  } else if (username.length < 3) {
    showFieldError(usernameInput, usernameError, 'Username must be at least 3 characters');
    valid = false;
  } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    showFieldError(usernameInput, usernameError, 'Username can only contain letters, numbers, and underscores');
    valid = false;
  }

  // Phone (optional)
  const phone = phoneInput.value.trim();
  if (phone && !isValidPhone(phone)) {
    showFieldError(phoneInput, phoneError, 'Please enter a valid phone number');
    valid = false;
  }

  // Password
  const password = passwordInput.value;
  if (!password) {
    showFieldError(passwordInput, passwordError, 'Password is required');
    valid = false;
  } else if (password.length < 8) {
    showFieldError(passwordInput, passwordError, 'Password must be at least 8 characters');
    valid = false;
  } else {
    const strength = getPasswordStrength(password);
    if (strength < 4) {
      showFieldError(passwordInput, passwordError, 'Password does not meet all strength requirements');
      valid = false;
    }
  }

  // Confirm password
  if (!validatePasswordMatch()) {
    valid = false;
  }

  return { valid };
}

function validatePasswordMatch() {
  const password = passwordInput.value;
  const confirm = passwordConfirmInput.value;

  if (!confirm) {
    showFieldError(passwordConfirmInput, passwordConfirmError, 'Please confirm your password');
    return false;
  }

  if (password !== confirm) {
    showFieldError(passwordConfirmInput, passwordConfirmError, 'Passwords do not match');
    return false;
  }

  clearFieldError(passwordConfirmInput, passwordConfirmError);
  return true;
}

function handleValidationErrors(errors) {
  // Safe, user-friendly messages for each field — never uses raw backend text.
  const safeMessages = {
    first_name: 'Please enter a valid first name.',
    last_name: 'Please enter a valid last name.',
    email: 'Please enter a valid email address.',
    username: 'Please choose a different username.',
    phone: 'Please enter a valid phone number.',
    password: 'Password does not meet the requirements. Use 8+ characters with an uppercase letter, a number, and a special character.',
    password_confirm: 'Passwords do not match.',
  };

  // Map DRF field names to our form fields
  const fieldMap = {
    first_name: { input: firstNameInput, error: firstNameError },
    last_name: { input: lastNameInput, error: lastNameError },
    email: { input: emailInput, error: emailError },
    username: { input: usernameInput, error: usernameError },
    phone: { input: phoneInput, error: phoneError },
    password: { input: passwordInput, error: passwordError },
    password_confirm: { input: passwordConfirmInput, error: passwordConfirmError },
    non_field_errors: null,
  };

  let hasFieldErrors = false;

  for (const [field, messages] of Object.entries(errors)) {
    if (field === 'non_field_errors') {
      // Non-field errors — show as form-level error, safe message only
      showFormError('Registration failed. Please check your details and try again.');
      continue;
    }

    const mapping = fieldMap[field];
    if (mapping) {
      // Always use the safe static message, never the raw backend message
      showFieldError(mapping.input, mapping.error, safeMessages[field] || 'Please check this field.');
      hasFieldErrors = true;
    }
  }

  // If only non-field errors, show form error
  if (!hasFieldErrors && errors.non_field_errors) {
    showFormError(Array.isArray(errors.non_field_errors) ? errors.non_field_errors.join('\n') : errors.non_field_errors);
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

function clearAllFieldErrors() {
  const fields = [
    [firstNameInput, firstNameError],
    [lastNameInput, lastNameError],
    [emailInput, emailError],
    [usernameInput, usernameError],
    [phoneInput, phoneError],
    [passwordInput, passwordError],
    [passwordConfirmInput, passwordConfirmError],
  ];
  fields.forEach(([input, errorEl]) => clearFieldError(input, errorEl));
}

function showFormError(message) {
  formErrorMessage.textContent = message;
  formError.classList.remove('hidden');
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

  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ============================================================
// Password Toggle & Strength
// ============================================================
function togglePasswordVisibility(input, eyeOpen, eyeClosed) {
  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';
  eyeOpen.style.display = isPassword ? 'none' : '';
  eyeClosed.style.display = isPassword ? '' : 'none';
}

function getPasswordStrength(password) {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  return score;
}

function updatePasswordStrength(password) {
  if (!password) {
    passwordStrength.style.display = 'none';
    return;
  }

  passwordStrength.style.display = '';
  const score = getPasswordStrength(password);

  // Update bar
  strengthBar.setAttribute('data-level', score);

  // Update count text
  passwordStrengthCount.setAttribute('data-level', score);
  passwordStrengthCount.textContent = `${score} of 4 requirements met`;

  // Update individual rules
  const checks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };

  strengthRules.forEach((rule) => {
    const ruleName = rule.getAttribute('data-rule');
    if (checks[ruleName]) {
      rule.classList.add('password-strength__rule--met');
    } else {
      rule.classList.remove('password-strength__rule--met');
    }
  });
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidPhone(phone) {
  // Basic phone validation - allows international format
  return /^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{4,10}$/.test(phone);
}