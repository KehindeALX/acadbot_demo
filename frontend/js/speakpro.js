import {
  speakProAnalyze,
  speakProFeedback,
  safeErrorMessage,
  guideErrorMessage,
  isNetworkError,
} from './api.js';
import { initNavbar } from './navbar.js';

const spForm = document.getElementById('spForm');
const spFormEl = document.getElementById('spFormEl');
const spFormError = document.getElementById('spFormError');
const spSubmit = document.getElementById('spSubmit');
const spLoading = document.getElementById('spLoading');
const spResult = document.getElementById('spResult');
const spPractice = document.getElementById('spPractice');
const spFeedback = document.getElementById('spFeedback');
const toastContainer = document.getElementById('toastContainer');
const stepEls = [
  document.getElementById('spStep1'),
  document.getElementById('spStep2'),
  document.getElementById('spStep3'),
];

const spSkills = document.getElementById('spSkills');
const spProject = document.getElementById('spProject');
const spGoal = document.getElementById('spGoal');

const fields = [
  { input: spSkills, counter: document.getElementById('spSkillsCount') },
  { input: spProject, counter: document.getElementById('spProjectCount') },
  { input: spGoal, counter: document.getElementById('spGoalCount') },
];

let analysis = null;
let busy = false;

document.addEventListener('DOMContentLoaded', async () => {
  const user = await initNavbar();
  if (!user) {
    window.location.href = 'login.html?redirect=speakpro.html';
    return;
  }
  wireCounters();
  wireForm();
});

function wireCounters() {
  fields.forEach(({ input, counter }) => {
    const update = () => {
      counter.textContent = String(input.value.length);
    };
    input.addEventListener('input', update);
    update();
  });
}

function wireForm() {
  spFormEl.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (busy) return;

    const skills = spSkills.value.trim();
    const project = spProject.value.trim();
    const goal = spGoal.value.trim();

    if (!skills || !project || !goal) {
      spFormError.textContent = 'Answer all three so we can work with something real.';
      spFormError.classList.add('visible');
      return;
    }
    spFormError.textContent = '';
    spFormError.classList.remove('visible');

    setBusy(true);
    try {
      analysis = await speakProAnalyze({ skills, project, goal });
      renderAnalysis(analysis);
      renderPractice(analysis.questions);
      goToStep(2);
      spResult.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  });
}

function setBusy(value) {
  busy = value;
  spSubmit.disabled = value;
  spSubmit.textContent = value ? 'Working...' : 'Find my gaps';
  spLoading.hidden = !value;
}

function goToStep(step) {
  stepEls.forEach((el, index) => {
    const reached = index < step;
    el.classList.toggle('sp-step--active', index + 1 === step);
    el.classList.toggle('sp-step--done', reached);
    if (index + 1 === step) {
      el.setAttribute('aria-current', 'step');
    } else {
      el.removeAttribute('aria-current');
    }
  });
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function heading(text, className) {
  return el('h2', className || 'sp-h2', text);
}

function renderAnalysis(data) {
  clear(spResult);
  spResult.classList.remove('hidden');

  spResult.appendChild(heading('Here is how you come across', 'sp-h2'));
  spResult.appendChild(el('p', 'sp-summary', data.summary));

  const card = el('section', 'sp-scorecard');
  const cardTitle = el('h3', 'sp-scorecard__title', 'How you score right now');
  card.appendChild(cardTitle);

  const list = el('div', 'sp-bars');
  data.dimensions.forEach((dimension) => {
    const row = el('div', 'sp-bar');
    const head = el('div', 'sp-bar__head');
    head.appendChild(el('span', 'sp-bar__name', dimension.name));
    head.appendChild(el('span', 'sp-bar__score', `${dimension.score}/5`));
    row.appendChild(head);

    const track = el('div', 'sp-bar__track');
    const fill = el('div', 'sp-bar__fill');
    fill.style.width = `${(dimension.score / 5) * 100}%`;
    track.appendChild(fill);
    row.appendChild(track);
    row.appendChild(el('p', 'sp-bar__note', dimension.note));

    list.appendChild(row);
  });
  card.appendChild(list);
  spResult.appendChild(card);

  if (data.gaps.length) {
    spResult.appendChild(heading('Where you are losing people', 'sp-h3'));
    const gaps = el('ul', 'sp-list');
    data.gaps.forEach((gap) => gaps.appendChild(el('li', 'sp-list__item', gap)));
    spResult.appendChild(gaps);
  }
}

function renderPractice(questions) {
  clear(spPractice);
  spPractice.classList.remove('hidden');

  spPractice.appendChild(heading('Now practise out loud', 'sp-h2'));
  spPractice.appendChild(el('p', 'sp-lede', 'Answer these the way you would in a real room. Plain, like you are talking to a person. There is no wrong answer here, only practice.'));

  const answers = [];
  questions.forEach((question, index) => {
    const block = el('div', 'sp-question');
    block.appendChild(el('h3', 'sp-question__title', `Question ${index + 1}`));
    block.appendChild(el('p', 'sp-question__text', question));

    const textarea = el('textarea', 'form-input sp-input');
    textarea.rows = 4;
    textarea.maxLength = 800;
    textarea.placeholder = 'Type or dictate your answer...';
    textarea.setAttribute('aria-label', `Your answer to question ${index + 1}`);

    const counter = el('div', 'sp-counter', '0 / 800');
    textarea.addEventListener('input', () => {
      counter.textContent = `${textarea.value.length} / 800`;
    });

    block.appendChild(textarea);
    block.appendChild(counter);
    spPractice.appendChild(block);

    answers.push({ question, textarea });
  });

  const error = el('p', 'form-error');
  error.setAttribute('role', 'alert');

  const button = el('button', 'btn btn--primary btn--lg sp-submit');
  button.type = 'button';
  button.textContent = 'Get my feedback';

  button.addEventListener('click', async () => {
    if (busy) return;

    const payload = answers.map(({ question, textarea }) => ({
      question,
      answer: textarea.value.trim(),
    }));

    if (payload.some((item) => !item.answer)) {
      error.textContent = 'Answer all three questions so there is something to work on.';
      error.classList.add('visible');
      return;
    }
    error.textContent = '';
    error.classList.remove('visible');

    busy = true;
    button.disabled = true;
    button.textContent = 'Working...';

    try {
      const data = await speakProFeedback(payload);
      renderFeedback(data, analysis.pitch);
      goToStep(3);
      spFeedback.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      showError(err);
    } finally {
      busy = false;
      button.disabled = false;
      button.textContent = 'Get my feedback';
    }
  });

  spPractice.appendChild(error);
  spPractice.appendChild(button);
}

function renderFeedback(data, pitch) {
  clear(spFeedback);
  spFeedback.classList.remove('hidden');

  spFeedback.appendChild(heading('How your answers landed', 'sp-h2'));
  spFeedback.appendChild(el('p', 'sp-summary', data.overall));

  const columns = el('div', 'sp-columns');

  const strengths = el('section', 'sp-column');
  strengths.appendChild(el('h3', 'sp-column__title', 'What worked'));
  const strengthList = el('ul', 'sp-list');
  data.strengths.forEach((item) => strengthList.appendChild(el('li', 'sp-list__item', item)));
  strengths.appendChild(strengthList);
  columns.appendChild(strengths);

  const improve = el('section', 'sp-column');
  improve.appendChild(el('h3', 'sp-column__title', 'What to change'));
  const improveList = el('ul', 'sp-list');
  data.improve.forEach((item) => improveList.appendChild(el('li', 'sp-list__item', item)));
  improve.appendChild(improveList);
  columns.appendChild(improve);

  spFeedback.appendChild(columns);

  spFeedback.appendChild(heading('Your answers, said better', 'sp-h3'));
  data.rewrites.forEach((rewrite, index) => {
    const block = el('div', 'sp-rewrite');
    block.appendChild(el('p', 'sp-rewrite__question', `${index + 1}. ${rewrite.question}`));
    block.appendChild(el('p', 'sp-rewrite__answer', rewrite.better_answer));
    spFeedback.appendChild(block);
  });

  const card = el('section', 'sp-pitch');
  card.id = 'spPitchCard';
  card.appendChild(el('p', 'sp-pitch__label', 'Your project pitch'));
  card.appendChild(el('h3', 'sp-pitch__headline', pitch.headline));
  card.appendChild(el('p', 'sp-pitch__one-liner', pitch.one_liner));
  const points = el('ul', 'sp-pitch__points');
  pitch.points.forEach((point) => points.appendChild(el('li', null, point)));
  card.appendChild(points);
  spFeedback.appendChild(card);

  const actions = el('div', 'sp-actions');

  const printBtn = el('button', 'btn btn--primary');
  printBtn.type = 'button';
  printBtn.textContent = 'Print or save as PDF';
  printBtn.addEventListener('click', () => window.print());

  const resetBtn = el('button', 'btn btn--secondary');
  resetBtn.type = 'button';
  resetBtn.textContent = 'Start over';
  resetBtn.addEventListener('click', startOver);

  actions.appendChild(printBtn);
  actions.appendChild(resetBtn);
  spFeedback.appendChild(actions);

  spFeedback.appendChild(el('p', 'sp-disclaimer', 'This is AI generated feedback, not a human coach. Do not enter private or sensitive personal details.'));
}

function startOver() {
  analysis = null;
  spFormEl.reset();
  fields.forEach(({ counter }) => {
    counter.textContent = '0';
  });
  clear(spResult);
  clear(spPractice);
  clear(spFeedback);
  spResult.classList.add('hidden');
  spPractice.classList.add('hidden');
  spFeedback.classList.add('hidden');
  spForm.classList.remove('hidden');
  spFormError.textContent = '';
  spFormError.classList.remove('visible');
  goToStep(1);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showError(err) {
  if (isNetworkError(err)) {
    showToast('We could not reach SpeakPro. Check your connection and try again.', 'error');
    return;
  }

  if ([429, 502, 503].includes(err.status)) {
    showToast(guideErrorMessage(err), 'error');
    return;
  }

  if (err.status === 400) {
    showToast(safeErrorMessage(err), 'error');
    return;
  }

  showToast(safeErrorMessage(err), 'error');
}

function showToast(message, type = 'info') {
  const toast = el('div', `toast toast--${type}`);
  toast.setAttribute('role', 'alert');
  const content = el('div', 'toast__content');
  content.appendChild(el('div', 'toast__message', message));
  toast.appendChild(content);
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
