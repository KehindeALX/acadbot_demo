/**
 * MSA AcadBot — Payment Return Page
 * Paystack sends the student back here after a payment. The server decides
 * whether access was granted, so this page only ever reports what it is told.
 */

import { verifyPayment, isAuthError } from './api.js';
import { initNavbar } from './navbar.js';

const returnIcon = document.getElementById('returnIcon');
const returnTitle = document.getElementById('returnTitle');
const returnMessage = document.getElementById('returnMessage');
const returnActions = document.getElementById('returnActions');

const PENDING_POLL_LIMIT = 10;
const PENDING_POLL_INTERVAL = 4000;

let checks = 0;

document.addEventListener('DOMContentLoaded', confirmPayment);

async function confirmPayment() {
  await initNavbar();

  const reference = new URLSearchParams(window.location.search).get('reference');
  if (!reference) {
    renderState({
      icon: '⚠️',
      title: 'We could not find that payment',
      message: 'This link is missing its payment reference. Start again from the course page.',
      actions: [courseLink(), coursesLink()],
    });
    return;
  }

  renderState({
    icon: '⏳',
    title: 'Confirming your payment',
    message: 'Hang on while we check with Paystack. This usually takes a few seconds.',
  });

  try {
    const data = await verifyPayment(reference);
    const state = data?.data || {};

    if (state.active) {
      renderState({
        icon: '✅',
        title: 'All lessons unlocked',
        message: expiresMessage(state.expires_at),
      });
      setTimeout(reloadCourse, 1500);
      return;
    }

    if (state.pending) {
      renderState({
        icon: '⏳',
        title: 'Your payment is still processing',
        message: 'Your bank has not confirmed it yet. Give it a moment, then check again.',
        actions: [checkAgainButton()],
      });
      return;
    }

    renderState({
      icon: '✕',
      title: 'That payment did not go through',
      message: 'Nothing was charged, and nothing on your account has changed. You can try again from the course page.',
      actions: [coursesLink()],
    });
  } catch (err) {
    renderError(err);
  }
}

function renderError(err) {
  if (isAuthError(err)) {
    renderState({
      icon: '🔒',
      title: 'Please sign in again',
      message: 'Your session ended while you were away. Sign in and the payment will be waiting for you.',
      actions: [{ label: 'Sign in', href: 'login.html' }],
    });
    return;
  }

  if (err.status === 400 || err.status === 404) {
    renderState({
      icon: '⏳',
      title: 'Your payment is still processing',
      message: 'Paystack has not finished with this payment yet. Give it a moment, then check again.',
      actions: [coursesLink()],
    });
    return;
  }

  renderState({
    icon: '⚠️',
    title: 'We could not confirm your payment',
    message: 'Something went wrong on our side, not in your payment. Your access will unlock on its own once Paystack confirms it.',
    actions: [coursesLink()],
  });
}

function renderState({ icon, title, message, actions = [] }) {
  returnIcon.textContent = icon;
  returnTitle.textContent = title;
  returnMessage.textContent = message;
  returnActions.innerHTML = '';
  actions.forEach(action => {
    const element = action.href
      ? document.createElement('a')
      : document.createElement('button');
    element.className = `btn ${action.primary ? 'btn--primary' : 'btn--secondary'}`;
    if (action.href) {
      element.href = action.href;
    } else {
      element.type = 'button';
      element.addEventListener('click', action.onClick);
    }
    element.textContent = action.label;
    returnActions.appendChild(element);
  });
}

function checkAgainButton() {
  return {
    label: 'Check again',
    primary: true,
    onClick: () => {
      checks += 1;
      if (checks >= PENDING_POLL_LIMIT) {
        reloadCourse();
        return;
      }
      renderState({
        icon: '⏳',
        title: 'Still checking',
        message: `Paystack has not confirmed this payment yet. Checking again in a moment. (${checks} of ${PENDING_POLL_LIMIT})`,
      });
      setTimeout(confirmPayment, PENDING_POLL_INTERVAL);
    },
  };
}

function courseLink() {
  const courseId = sessionStorage.getItem('pendingCourseId');
  return courseId
    ? { label: 'Back to the course', href: `course-detail.html?id=${encodeURIComponent(courseId)}`, primary: true }
    : { label: 'Browse courses', href: 'courses.html', primary: true };
}

function coursesLink() {
  return { label: 'Browse courses', href: 'courses.html' };
}

function reloadCourse() {
  const courseId = sessionStorage.getItem('pendingCourseId');
  window.location.href = courseId
    ? `course-detail.html?id=${encodeURIComponent(courseId)}`
    : 'courses.html';
}

function expiresMessage(expiresAt) {
  if (!expiresAt) return 'Every lesson and quiz is now open to you.';
  const date = new Date(expiresAt);
  const readable = date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  return `Every lesson and quiz is open to you until ${readable}. Taking you back...`;
}
