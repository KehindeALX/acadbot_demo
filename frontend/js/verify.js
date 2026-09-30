/**
 * MSA AcadBot — Public Certificate Verification Page
 * No authentication required. Reads ?code= from the URL or the form.
 */

import { verifyCertificate } from './api.js';
import { initNavbar } from './navbar.js';

const verifyForm = document.getElementById('verifyForm');
const certCode = document.getElementById('certCode');
const verifyBtn = document.getElementById('verifyBtn');
const verifyStatus = document.getElementById('verifyStatus');

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();

  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  if (code) {
    certCode.value = code;
    runVerification(code);
  }
});

verifyForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const code = certCode.value.trim();
  if (!code) {
    showMessage('Enter a certificate ID first.');
    return;
  }
  runVerification(code);
});

async function runVerification(code) {
  verifyBtn.disabled = true;
  verifyBtn.textContent = 'Verifying...';
  verifyStatus.textContent = '';

  try {
    const res = await verifyCertificate(code);
    renderResult(res.data);
  } catch (err) {
    showMessage('We could not find a certificate with that ID. Check the code and try again.');
  } finally {
    verifyBtn.disabled = false;
    verifyBtn.textContent = 'Verify';
  }
}

function renderResult(data) {
  verifyStatus.textContent = '';

  const card = document.createElement('div');
  card.className = 'cert-verify-result';

  const name = document.createElement('p');
  name.className = 'cert-verify-result__name';
  name.textContent = data.holder_name;

  const course = document.createElement('p');
  course.className = 'cert-card__meta';
  course.textContent = data.course_title;

  const date = document.createElement('p');
  date.className = 'cert-card__meta';
  date.textContent = `Issued ${new Date(data.issued_at).toLocaleDateString()}`;

  const valid = document.createElement('span');
  valid.className = 'cert-verify-result__valid';
  valid.textContent = data.valid ? 'Valid Certificate' : 'Invalid Certificate';

  card.append(name, course, date, valid);
  verifyStatus.appendChild(card);
}

function showMessage(text) {
  verifyStatus.textContent = '';

  const card = document.createElement('div');
  card.className = 'cert-verify-result';
  const msg = document.createElement('p');
  msg.className = 'cert-card__meta';
  msg.textContent = text;
  card.appendChild(msg);
  verifyStatus.appendChild(card);
}
