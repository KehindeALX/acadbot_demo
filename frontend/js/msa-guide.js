/**
 * MSA AcadBot — "MSA AI Guide" Page Logic
 *
 * Renders the Abia career guide: a welcome screen with career cards,
 * and a journey screen with stage tabs (Roadmap, Skills, Interview, Courses)
 * plus a chat interface.
 *
 * INTEGRATION NOTE (read before wiring the backend):
 * No chat/AI endpoint exists yet on the backend (PRODUCT.md principle #2 —
 * no invented endpoints). This module is built to be *ready to call*: when
 * a chat endpoint is routed, replace the placeholder body of `guideAbia()`
 * in ./api.js with the real call, and this page works unchanged.
 *
 * Career data (cards, roadmap, skills, questions) comes from real API
 * endpoints (/api/careers/, /api/careers/{slug}/).
 */

import {
  getMe,
  listCareers,
  getCareer,
  guideAbia,
  formatApiError,
  isAuthError,
  isNetworkError
} from './api.js';

// ============================================================
// DOM Elements
// ============================================================
const guideWelcome = document.getElementById('guideWelcome');
const guideJourney = document.getElementById('guideJourney');
const careersGrid = document.getElementById('careersGrid');
const careersLoading = document.getElementById('careersLoading');
const careersEmpty = document.getElementById('careersEmpty');
const careersError = document.getElementById('careersError');
const retryCareersBtn = document.getElementById('retryCareersBtn');

const backBtn = document.getElementById('backBtn');
const journeyIcon = document.getElementById('journeyIcon');
const journeyName = document.getElementById('journeyName');
const journeyTag = document.getElementById('journeyTag');
const guideThread = document.getElementById('guideThread');
const guideInput = document.getElementById('guideInput');
const guideSend = document.getElementById('guideSend');
const authNav = document.getElementById('authNav');
const toastContainer = document.getElementById('toastContainer');

// ============================================================
// State
// ============================================================
let user = null;
let careers = [];
let activeCareer = null;
let activeStage = 'roadmap';
let isSending = false;
let messageCount = 0;
let skillStates = {}; // { skillId: true/false }

// Composer auto-resize bounds
const INPUT_MIN_HEIGHT = 52;
const INPUT_MAX_HEIGHT = 150;

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  await checkAuthState();
  await loadCareers();
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
      renderAuthNav(); // Not logged in — guide stays available
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
// Load Careers
// ============================================================
async function loadCareers() {
  showCareersLoading(true);
  careersEmpty.classList.add('hidden');
  careersError.classList.add('hidden');

  try {
    const data = await listCareers();
    careers = data.results || [];

    if (careers.length === 0) {
      careersEmpty.classList.remove('hidden');
      careersGrid.classList.add('hidden');
    } else {
      renderCareerCards();
      careersGrid.classList.remove('hidden');
    }
  } catch (err) {
    careersError.classList.remove('hidden');
    careersGrid.classList.add('hidden');
    if (!isNetworkError(err)) {
      showToast(formatApiError(err), 'error');
    }
  } finally {
    showCareersLoading(false);
  }
}

function showCareersLoading(show) {
  careersLoading.classList.toggle('hidden', !show);
  if (show) careersGrid.classList.add('hidden');
}

function renderCareerCards() {
  careersGrid.innerHTML = '';

  // Career-specific icons (fallback if API doesn't provide one)
  const defaultIcons = {
    data: '📊',
    cyber: '🔐',
    software: '💻',
    ai: '🤖',
    uiux: '🎨',
    product: '🗺️',
    digital: '📱',
    cloud: '☁️',
  };

  careers.forEach(career => {
    const card = document.createElement('article');
    card.className = 'guide__career-card';
    card.setAttribute('role', 'listitem');
    card.setAttribute('tabindex', '0');
    card.setAttribute('aria-label', `Explore ${career.name} career path`);

    const icon = career.icon || defaultIcons[career.slug] || '🎯';
    const skillsCount = career.skills_count || 0;
    const stagesCount = career.roadmap_stages_count || 0;

    card.innerHTML = `
      <div class="guide__career-card-icon">${icon}</div>
      <h3 class="guide__career-card-name">${escapeHtml(career.name)}</h3>
      ${career.tag ? `<span class="guide__career-card-tag">${escapeHtml(career.tag)}</span>` : ''}
      <div class="guide__career-card-meta">
        <span>${stagesCount} steps</span>
        <span>${skillsCount} skills</span>
      </div>
    `;

    card.addEventListener('click', () => enterJourney(career));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        enterJourney(career);
      }
    });

    careersGrid.appendChild(card);
  });
}

// ============================================================
// Journey Flow
// ============================================================
async function enterJourney(career) {
  // Show loading state
  guideWelcome.classList.add('hidden');
  guideJourney.classList.remove('hidden');

  // Set header
  const defaultIcons = {
    data: '📊', cyber: '🔐', software: '💻', ai: '🤖',
    uiux: '🎨', product: '🗺️', digital: '📱', cloud: '☁️',
  };
  journeyIcon.textContent = career.icon || defaultIcons[career.slug] || '🎯';
  journeyName.textContent = career.name;
  journeyTag.textContent = career.tag || '';

  // Reset state
  activeCareer = career;
  activeStage = 'roadmap';
  messageCount = 0;
  skillStates = {};
  guideThread.innerHTML = '';
  updateActiveTab();

  // Fetch full career detail
  try {
    const detail = await getCareer(career.slug);
    activeCareer = { ...activeCareer, ...detail };
  } catch (err) {
    showToast('Could not load career details. Showing limited info.', 'warning');
  }

  // Load the initial stage
  loadStage(activeStage);

  // Focus input
  setTimeout(() => guideInput.focus(), 100);
}


function exitJourney() {
  guideJourney.classList.add('hidden');
  guideWelcome.classList.remove('hidden');
  activeCareer = null;
  activeStage = 'roadmap';
  messageCount = 0;
  guideThread.innerHTML = '';
}

// ============================================================
// Stage Tabs
// ============================================================
function setupStageTabs() {
  document.querySelectorAll('.guide__stage-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const stage = tab.dataset.stage;
      if (stage === activeStage) return;
      activeStage = stage;
      updateActiveTab();
      loadStage(stage);
    });
  });
}

function updateActiveTab() {
  document.querySelectorAll('.guide__stage-tab').forEach(tab => {
    const isActive = tab.dataset.stage === activeStage;
    tab.classList.toggle('guide__stage-tab--active', isActive);
    tab.setAttribute('aria-selected', isActive);
  });
}

// ============================================================
// Stage Loading
// ============================================================
function loadStage(stage) {
  // Clear thread for new stage
  guideThread.innerHTML = '';
  messageCount = 0;

  switch (stage) {
    case 'roadmap':
      renderRoadmapStage();
      break;
    case 'skills':
      renderSkillsStage();
      break;
    case 'interview':
      renderInterviewStage();
      break;
    case 'courses':
      renderCoursesStage();
      break;
  }
}

// --- Roadmap Stage ---
function renderRoadmapStage() {
  const stages = activeCareer.roadmap_stages || [];

  if (stages.length === 0) {
    appendBotMessage('The roadmap for this career path hasn\'t been added yet. Check back soon!');
    return;
  }

  // Sort by order
  const sorted = [...stages].sort((a, b) => (a.order || 0) - (b.order || 0));

  let html = `<div class="guide__roadmap">`;
  sorted.forEach((step, i) => {
    html += `
      <div class="guide__rm-step">
        <span class="guide__rm-num">${i + 1}</span>
        <div class="guide__rm-body">
          <strong>${escapeHtml(step.title || step.name || '')}</strong>
          ${step.description ? `<p>${escapeHtml(step.description)}</p>` : ''}
        </div>
      </div>
    `;
  });
  html += `</div>`;

  appendBotMessage(`Here's your <strong>${escapeHtml(activeCareer.name)}</strong> roadmap — ${sorted.length} steps to guide your journey:`, html);
}

// --- Skills Stage ---
function renderSkillsStage() {
  const skills = activeCareer.skills || [];

  if (skills.length === 0) {
    appendBotMessage('Skills for this career path haven\'t been added yet. Check back soon!');
    return;
  }

  let html = `<div class="guide__skills">`;
  skills.forEach(skill => {
    const id = skill.id || skill.name;
    if (skillStates[id] === undefined) skillStates[id] = null;

    html += `
      <div class="guide__skill-item" data-skill-id="${id}">
        <span class="guide__skill-name">${escapeHtml(skill.name || skill.skill || '')}</span>
        ${skill.description ? `<span class="guide__skill-desc">${escapeHtml(skill.description)}</span>` : ''}
        <div class="guide__skill-actions">
          <button class="guide__skill-btn guide__skill-btn--yes" data-skill="${id}" data-value="true" aria-label="I have this skill">Yes</button>
          <button class="guide__skill-btn guide__skill-btn--no" data-skill="${id}" data-value="false" aria-label="I need this skill">No</button>
        </div>
      </div>
    `;
  });
  html += `</div>`;

  appendBotMessage(`Let's check your skills for <strong>${escapeHtml(activeCareer.name)}</strong>. Mark each one as "Yes" (I have it) or "No" (I need it):`, html);

  // Attach skill button handlers
  guideThread.querySelectorAll('.guide__skill-btn').forEach(btn => {
    btn.addEventListener('click', () => handleSkillToggle(btn.dataset.skill, btn.dataset.value === 'true'));
  });
}

function handleSkillToggle(skillId, hasSkill) {
  skillStates[skillId] = hasSkill;

  // Update button visuals
  const item = guideThread.querySelector(`.guide__skill-item[data-skill-id="${skillId}"]`);
  if (!item) return;

  item.querySelectorAll('.guide__skill-btn').forEach(btn => {
    btn.classList.remove('guide__skill-btn--selected');
  });

  const selectedBtn = item.querySelector(`.guide__skill-btn[data-value="${hasSkill}"]`);
  if (selectedBtn) selectedBtn.classList.add('guide__skill-btn--selected');

  // Check if all skills answered
  const allSkills = activeCareer.skills || [];
  const allAnswered = allSkills.every(s => {
    const id = s.id || s.name;
    return skillStates[id] !== null;
  });

  if (allAnswered) {
    const haveCount = allSkills.filter(s => skillStates[s.id || s.name] === true).length;
    const needCount = allSkills.length - haveCount;
    appendBotMessage(`Great self-assessment! You have <strong>${haveCount}</strong> skill${haveCount !== 1 ? 's' : ''} and need to develop <strong>${needCount}</strong>. ${needCount > 0 ? 'Check the Roadmap tab for your learning path, or explore the Courses tab for relevant MSA courses.' : 'You\'re in great shape for this career path! 🎉'}`);
  }
}

// --- Interview Stage ---
function renderInterviewStage() {
  const questions = activeCareer.interview_questions || [];

  if (questions.length === 0) {
    appendBotMessage('Interview questions for this career path haven\'t been added yet. Check back soon!');
    return;
  }

  // Sort by order and show the first question
  const sorted = [...questions].sort((a, b) => (a.order || 0) - (b.order || 0));
  let currentQIndex = 0;

  function showQuestion(index) {
    if (index >= sorted.length) {
      appendBotMessage('🎉 You\'ve completed all the interview questions for this career path! Great preparation.');
      return;
    }

    const q = sorted[index];
    let html = `<div class="guide__interview-q">`;
    html += `<div class="guide__interview-badge">Question ${index + 1} of ${sorted.length}</div>`;
    html += `<p class="guide__interview-question">${escapeHtml(q.question || q.text || '')}</p>`;
    if (q.category) {
      html += `<span class="guide__interview-category">${escapeHtml(q.category)}</span>`;
    }
    html += `</div>`;

    appendBotMessage(`Time for interview prep! Here's question ${index + 1}:`, html);

    // Store the current question index for the chat handler
    guideThread.dataset.interviewIndex = index;
  }

  showQuestion(0);

  // Expose for chat handler
  window.__guideInterview = {
    questions: sorted,
    showNext: () => {
      currentQIndex++;
      showQuestion(currentQIndex);
    },
    getCurrent: () => sorted[currentQIndex] || null,
  };
}

// --- Courses Stage ---
function renderCoursesStage() {
  // Courses come from the career detail's related courses
  // The API may include them directly or we may need to note they're linked
  const courses = activeCareer.courses || [];

  if (courses.length === 0) {
    appendBotMessage(`There are no MSA courses linked to <strong>${escapeHtml(activeCareer.name)}</strong> yet. Browse all courses on the <a href="courses.html" class="guide__link">Courses page</a>.`);
    return;
  }

  let html = `<div class="guide__courses">`;
  courses.forEach(course => {
    const id = course.id || '';
    const title = course.title || 'Untitled Course';
    const lessonsCount = course.lessons_count || 0;

    html += `
      <a href="course-detail.html?id=${id}" class="guide__course-pill">
        <span class="guide__course-pill-title">${escapeHtml(title)}</span>
        <span class="guide__course-pill-meta">${lessonsCount} lesson${lessonsCount !== 1 ? 's' : ''}</span>
      </a>
    `;
  });
  html += `</div>`;

  appendBotMessage(`Here are the MSA courses that match <strong>${escapeHtml(activeCareer.name)}</strong>:`, html);
}

// ============================================================
// Chat — Composer (auto-resize)
// ============================================================
function autoResize() {
  guideInput.style.height = 'auto';
  const next = Math.min(Math.max(guideInput.scrollHeight, INPUT_MIN_HEIGHT), INPUT_MAX_HEIGHT);
  guideInput.style.height = `${next}px`;
}

// ============================================================
// Chat — Sending Messages
// ============================================================
function handleSend() {
  const text = guideInput.value.trim();
  if (!text || isSending) return;

  appendUserMessage(text);
  guideInput.value = '';
  autoResize();
  guideInput.focus();

  isSending = true;
  guideSend.disabled = true;
  showTyping();

  // For interview stage, treat user messages as interview answers
  if (activeStage === 'interview' && window.__guideInterview) {
    const currentQ = window.__guideInterview.getCurrent();
    if (currentQ) {
      // Call the AI stub for feedback on the answer
      guideAbia({ message: `Interview question: "${currentQ.question || currentQ.text}"\n\nUser's answer: "${text}"\n\nProvide brief, constructive feedback on this interview answer.`, career_slug: activeCareer?.slug })
        .then(reply => {
          removeTyping();
          if (reply && reply.success && reply.message) {
            appendBotMessage(reply.message);
          }
          // Show next question after a delay
          setTimeout(() => {
            window.__guideInterview.showNext();
          }, 1500);
        })
        .catch(() => {
          removeTyping();
          appendBotMessage('Thank you for your answer! Practice makes perfect. Let\'s move to the next question.');
          setTimeout(() => {
            window.__guideInterview.showNext();
          }, 1200);
        })
        .finally(() => {
          isSending = false;
          guideSend.disabled = false;
          scrollToBottom();
        });
      return;
    }
  }

  // Default: send to Abia stub
  guideAbia({ message: text, career_slug: activeCareer?.slug })
    .then(reply => {
      removeTyping();
      if (reply && reply.success && reply.message) {
        appendBotMessage(reply.message);
      }
    })
    .catch(err => {
      removeTyping();
      appendBotMessage('Abia isn\'t connected yet — your message was received. The career guide AI will respond here once it\'s wired to the backend.');
      if (isNetworkError(err)) {
        showToast('Unable to connect to the server.', 'warning');
      } else {
        showToast(formatApiError(err), 'error');
      }
    })
    .finally(() => {
      isSending = false;
      guideSend.disabled = false;
      scrollToBottom();
    });
}

// ============================================================
// Chat — Message Rendering
// ============================================================
function appendUserMessage(text) {
  appendMessage('user', text);
}

function appendBotMessage(text, richHtml) {
  appendMessage('bot', text, richHtml);
}

function appendMessage(role, text, richHtml) {
  const article = document.createElement('article');
  article.className = `guide-msg guide-msg--${role}`;
  article.setAttribute('role', 'listitem');

  const bubble = document.createElement('div');
  bubble.className = 'guide-msg__bubble';

  if (role === 'bot') {
    const avatar = document.createElement('span');
    avatar.className = 'guide-msg__avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = '🧭';
    bubble.appendChild(avatar);

    const content = document.createElement('div');
    content.className = 'guide-msg__content';
    // Allow HTML for rich messages (roadmap, skills, etc.)
    if (richHtml) {
      content.innerHTML = text ? `<p>${text}</p>${richHtml}` : richHtml;
    } else {
      content.textContent = text;
    }
    bubble.appendChild(content);
  } else {
    bubble.textContent = text;
  }

  article.appendChild(bubble);
  guideThread.appendChild(article);
  messageCount++;
  scrollToBottom();
}

function showTyping() {
  const typing = document.createElement('article');
  typing.className = 'guide-msg guide-msg--bot guide-msg--typing';
  typing.id = 'typingIndicator';
  typing.setAttribute('role', 'status');
  typing.setAttribute('aria-label', 'Abia is typing');
  typing.innerHTML = `
    <div class="guide-msg__bubble">
      <span class="guide-msg__avatar" aria-hidden="true">🧭</span>
      <div class="guide-msg__content guide-typing" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
  guideThread.appendChild(typing);
  scrollToBottom();
}

function removeTyping() {
  const typing = document.getElementById('typingIndicator');
  if (typing) typing.remove();
}

function scrollToBottom() {
  guideThread.scrollTop = guideThread.scrollHeight;
}

// ============================================================
// Event Listeners
// ============================================================
function setupEventListeners() {
  // Back button
  backBtn.addEventListener('click', exitJourney);

  // Retry careers load
  retryCareersBtn.addEventListener('click', loadCareers);

  // Send on button click
  guideSend.addEventListener('click', handleSend);

  // Send on Enter (Shift+Enter for newline)
  guideInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  // Auto-resize on input
  guideInput.addEventListener('input', autoResize);

  // Stage tabs
  setupStageTabs();
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
