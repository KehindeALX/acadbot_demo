/**
 * MSA AcadBot — Shared Navbar Module
 *
 * Provides auth-aware navbar rendering used by every page.
 * Import initNavbar() on DOMContentLoaded to automatically:
 *   1. Check auth state via GET /api/auth/me/
 *   2. Render authenticated nav (user name, Dashboard link, Logout button)
 *      or unauthenticated nav (Sign In, Sign Up)
 *   3. Wire up the Logout button
 */

import { getMe, isAuthError } from './api.js';

/**
 * Initialise the auth-aware navbar.
 * Call once per page on DOMContentLoaded.
 * Looks for <div id="authNav"> inside the navbar.
 * @returns {Promise<object|null>} The current user object, or null if not authenticated.
 */
export async function initNavbar() {
  const authNav = document.getElementById('authNav');
  if (!authNav) return null;

  try {
    const data = await getMe();
    if (data.success && data.data) {
      renderAuthNav(authNav, data.data);
      return data.data;
    }
    renderGuestNav(authNav);
  } catch (err) {
    if (isAuthError(err)) {
      renderGuestNav(authNav);
    }
    // Network errors — leave authNav empty, don't block page
  }
  return null;
}

/**
 * Render the authenticated navbar items.
 * Layout: [User Name] [Dashboard] | [Logout]
 * Logout is always the last item.
 */
function renderAuthNav(container, user) {
  const displayName = [user.first_name, user.last_name]
    .filter(Boolean)
    .join(' ') || user.username;

  container.innerHTML = `
    <span class="navbar__user-name">${escapeHtml(displayName)}</span>
    <a href="dashboard.html" class="navbar__link">Dashboard</a>
    <button id="logoutBtn" class="navbar__btn">Logout</button>
  `;

  document.getElementById('logoutBtn').addEventListener('click', handleLogout);
}

/**
 * Render the unauthenticated navbar items.
 */
function renderGuestNav(container) {
  container.innerHTML = `
    <a href="login.html" class="navbar__link navbar__btn">Sign In</a>
    <a href="register.html" class="navbar__link navbar__btn">Sign Up</a>
  `;
}

/**
 * Handle logout — call API, then redirect to login page.
 * Exported so pages that need extra cleanup (e.g. course-detail re-rendering its
 * enrollment UI first) can remove this listener and wire their own.
 */
export async function handleLogout() {
  const { logout } = await import('./api.js');
  try {
    await logout();
    window.location.href = 'login.html';
  } catch (err) {
    // Show error but stay on page — user can retry
    const toastContainer = document.getElementById('toastContainer');
    if (toastContainer) {
      const toast = document.createElement('div');
      toast.className = 'toast toast--error';
      toast.setAttribute('role', 'alert');
      toast.innerHTML = `
        <span class="toast__icon">✕</span>
        <div class="toast__content">
          <div class="toast__message">Logout failed. Please try again.</div>
        </div>
      `;
      toastContainer.appendChild(toast);
      setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
      }, 4000);
    }
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
