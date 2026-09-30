/**
 * MSA AcadBot — "Ask AcadBot" Chat Page Logic
 *
 * Renders the AI-assistant chat surface: a welcome/empty state with quick
 * actions, an auto-resizing composer, and a message thread.
 *
 * Replies come from POST /api/guide/chat/ via askAcadBot(). The conversation
 * is held in memory on this page only, so a refresh starts a new thread.
 */

import {
  guideErrorMessage,
  askAcadBot,
} from './api.js';
import { initNavbar } from './navbar.js';

// ============================================================
// DOM Elements
// ============================================================
const chatWelcome = document.getElementById('chatWelcome');
const chatThread = document.getElementById('chatThread');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');
const toastContainer = document.getElementById('toastContainer');

// ============================================================
// State
// ============================================================
let user = null;
let isSending = false;
let messageCount = 0;
let conversation = [];

// Composer auto-resize bounds
const INPUT_MIN_HEIGHT = 52;
const INPUT_MAX_HEIGHT = 150;

const HISTORY_LIMIT = 10;

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  user = await initNavbar();
  if (!user) {
    window.location.href = 'login.html?redirect=acadbot.html';
    return;
  }
  setupEventListeners();
  focusInput();
});

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

  const history = conversation.slice(-(HISTORY_LIMIT - 1));
  history.push({ role: 'user', content: text });

  askAcadBot(history)
    .then(data => {
      removeTyping();
      const reply = data && data.reply;
      if (!reply) return;
      conversation.push({ role: 'user', content: text });
      conversation.push({ role: 'assistant', content: reply });
      appendMessage('bot', reply);
    })
    .catch(err => {
      removeTyping();
      const message = guideErrorMessage(err);
      appendMessage('bot', message);
      showToast(message, 'error');
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
