/**
 * MSA AcadBot — "Ask AcadBot" Chat Page Logic
 *
 * Renders the AI-assistant chat surface: a welcome/empty state with quick
 * actions, an auto-resizing composer, and a message thread.
 *
 * INTEGRATION NOTE (read before wiring the backend):
 * No chat/AI endpoint exists yet on the backend (PRODUCT.md principle #2 —
 * no invented endpoints). This module is built to be *ready to call*: when
 * a chat endpoint is routed, replace the placeholder body of `askAcadBot()`
 * in ./api.js with the real call, and this page works unchanged.
 *
 * Until then, sending a message renders the user's message locally (real UI
 * behavior) and responds with an honest "assistant not connected yet" state
 * — never a fabricated AI answer.
 */

import {
  getMe,
  formatApiError,
  isAuthError,
  isNetworkError
} from './api.js';
import { askAcadBot } from './api.js';

// ============================================================
// DOM Elements
// ============================================================
const chatWelcome = document.getElementById('chatWelcome');
const chatThread = document.getElementById('chatThread');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');
const authNav = document.getElementById('authNav');
const toastContainer = document.getElementById('toastContainer');

// ============================================================
// State
// ============================================================
let user = null;
let isSending = false;
let messageCount = 0;

// Composer auto-resize bounds
const INPUT_MIN_HEIGHT = 52;
const INPUT_MAX_HEIGHT = 150;

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  await checkAuthState();
  setupEventListeners();
  focusInput();
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
      renderAuthNav(); // Not logged in — chat stays available
    } else if (isNetworkError(err)) {
      showToast('Unable to check login status', 'warning');
    }
  }
}

function renderAuthNav() {
  if (user) {
    const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;
    authNav.innerHTML = `
      <span class="navbar__user-name">${displayName}</span>
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
    renderAuthNav();
    showToast('Logged out successfully', 'success');
  } catch (err) {
    showToast('Logout failed', 'error');
  }
}

// ============================================================
// Composer (auto-resize)
// ============================================================
function focusInput() {
  chatInput.focus();
}

function autoResize() {
  chatInput.style.height = 'auto';
  const next = Math.min(Math.max(chatInput.scrollHeight, INPUT_MIN_HEIGHT), INPUT_MAX_HEIGHT);
  chatInput.style.height = `${next}px`;
}

// ============================================================
// Quick Actions
// ============================================================
function handleQuickAction(prompt) {
  chatInput.value = prompt;
  autoResize();
  focusInput();
  // Give the layout a beat to settle before the thread opens
  requestAnimationFrame(() => {
    chatInput.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
}

// ============================================================
// Sending Messages
// ============================================================
function handleSend() {
  const text = chatInput.value.trim();
  if (!text || isSending) return;

  // Reveal the thread on the first message
  if (messageCount === 0) {
    chatWelcome.classList.add('hidden');
    chatThread.classList.remove('hidden');
  }

  appendMessage('user', text);
  chatInput.value = '';
  autoResize();
  focusInput();

  isSending = true;
  chatSend.disabled = true;
  showTyping();

  // Call the (future) backend. askAcadBot currently returns a not-connected
  // result until a real chat endpoint is wired — no fake AI data.
  askAcadBot({ message: text })
    .then(reply => {
      removeTyping();
      if (reply && reply.success && reply.message) {
        appendMessage('bot', reply.message);
      }
    })
    .catch(err => {
      removeTyping();
      appendMessage('bot', 'AcadBot isn’t connected yet — your message was received. The AI assistant will respond here once it’s wired to the backend.');
      if (isNetworkError(err)) {
        showToast('Unable to connect to the server.', 'warning');
      } else {
        showToast(formatApiError(err), 'error');
      }
    })
    .finally(() => {
      isSending = false;
      chatSend.disabled = false;
      scrollToBottom();
    });
}

// ============================================================
// Message Rendering
// ============================================================
function appendMessage(role, text) {
  const article = document.createElement('article');
  article.className = `chat-msg chat-msg--${role}`;
  article.setAttribute('role', 'listitem');

  const bubble = document.createElement('div');
  bubble.className = 'chat-msg__bubble';

  if (role === 'bot') {
    const avatar = document.createElement('span');
    avatar.className = 'chat-msg__avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = '🤖';
    bubble.appendChild(avatar);

    const content = document.createElement('div');
    content.className = 'chat-msg__content';
    content.textContent = text;
    bubble.appendChild(content);
  } else {
    bubble.textContent = text;
  }

  article.appendChild(bubble);
  chatThread.appendChild(article);
  messageCount++;
  scrollToBottom();
}

function showTyping() {
  const typing = document.createElement('article');
  typing.className = 'chat-msg chat-msg--bot chat-msg--typing';
  typing.id = 'typingIndicator';
  typing.setAttribute('role', 'status');
  typing.setAttribute('aria-label', 'AcadBot is typing');
  typing.innerHTML = `
    <div class="chat-msg__bubble">
      <span class="chat-msg__avatar" aria-hidden="true">🤖</span>
      <div class="chat-msg__content chat-typing" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
  chatThread.appendChild(typing);
  scrollToBottom();
}

function removeTyping() {
  const typing = document.getElementById('typingIndicator');
  if (typing) typing.remove();
}

function scrollToBottom() {
  chatThread.scrollTop = chatThread.scrollHeight;
}

// ============================================================
// Event Listeners
// ============================================================
function setupEventListeners() {
  // Send on button click
  chatSend.addEventListener('click', handleSend);

  // Send on Enter (Shift+Enter for newline)
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  // Auto-resize on input
  chatInput.addEventListener('input', autoResize);

  // Quick actions
  document.querySelectorAll('.chat__quick-btn').forEach(btn => {
    btn.addEventListener('click', () => handleQuickAction(btn.dataset.prompt));
  });
}

// ============================================================
// Utilities
// ============================================================
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
