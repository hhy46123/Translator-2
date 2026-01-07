const items = window.NOTEBOOK_ITEMS || [];
const quizGrid = document.getElementById('quiz-grid');
const pageInfo = document.getElementById('page-info');
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const detailModal = document.getElementById('detail-modal');
const detailBody = document.getElementById('detail-body');
const closeDetail = document.getElementById('close-detail');
const feedbackModal = document.getElementById('feedback-modal');
const feedbackTitle = document.getElementById('feedback-title');
const feedbackText = document.getElementById('feedback-text');
const feedbackClose = document.getElementById('feedback-close');

const pageSize = 40;
let pageIndex = 0;

function wrongClass(wrongAttempts) {
  if (wrongAttempts >= 6) return 'high';
  if (wrongAttempts >= 3) return 'mid';
  if (wrongAttempts >= 1) return 'low';
  return '';
}

function maskText(text) {
  if (!text) return '';
  return text.replace(/\S/g, '•');
}

async function loadDetails(itemId) {
  const response = await fetch(`/api/notebook/${itemId}/details`);
  if (!response.ok) {
    detailBody.textContent = 'Failed to load details.';
    return;
  }
  const data = await response.json();
  const senses = data.senses || [];
  const html = senses.map((sense, index) => {
    const equivalents = (sense.en_equivalents || []).join(', ');
    const definition = sense.definition_ko || '';
    return `<div class="detail-sense"><strong>${index + 1}.</strong> ${equivalents} ${definition}</div>`;
  }).join('');
  detailBody.innerHTML = `
    <p><strong>Source:</strong> ${data.source_text}</p>
    <p><strong>Translation:</strong> ${data.translated_text}</p>
    <div>${html || '<em>No sense details.</em>'}</div>
  `;
  detailModal.classList.remove('hidden');
}

function showFeedback(title, text) {
  feedbackTitle.textContent = title;
  feedbackText.textContent = text;
  feedbackModal.classList.remove('hidden');
}

function renderPage() {
  quizGrid.innerHTML = '';
  const start = pageIndex * pageSize;
  const pageItems = items.slice(start, start + pageSize);
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  pageInfo.textContent = `Page ${pageIndex + 1} / ${totalPages}`;

  pageItems.forEach((item) => {
    const card = document.createElement('div');
    card.className = `quiz-item ${wrongClass(item.wrong_attempts)}`;

    const masked = document.createElement('div');
    masked.textContent = maskText(item.translated_text);
    masked.className = 'masked';

    const revealBtn = document.createElement('button');
    revealBtn.textContent = 'Reveal';
    revealBtn.addEventListener('click', () => {
      masked.textContent = item.translated_text;
    });

    const detailsBtn = document.createElement('button');
    detailsBtn.textContent = 'Details';
    detailsBtn.addEventListener('click', () => loadDetails(item.id));

    const correctBtn = document.createElement('button');
    correctBtn.textContent = 'Correct';
    correctBtn.addEventListener('click', async () => {
      await fetch(`/api/notebook/${item.id}/mark_correct`, { method: 'POST' });
      item.correct_count += 1;
      showFeedback('Correct', 'Nice work!');
    });

    const wrongBtn = document.createElement('button');
    wrongBtn.textContent = 'Wrong';
    wrongBtn.addEventListener('click', async () => {
      await fetch(`/api/notebook/${item.id}/wrong_delta`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delta: 1 })
      });
      item.wrong_attempts += 1;
      card.className = `quiz-item ${wrongClass(item.wrong_attempts)}`;
      showFeedback('Wrong', 'Keep practicing.');
    });

    const header = document.createElement('div');
    header.innerHTML = `<strong>${item.source_text}</strong>`;

    const actions = document.createElement('div');
    actions.className = 'quiz-actions';
    actions.append(revealBtn, correctBtn, wrongBtn, detailsBtn);

    card.append(header, masked, actions);
    quizGrid.appendChild(card);
  });
}

prevPageBtn.addEventListener('click', () => {
  if (pageIndex > 0) {
    pageIndex -= 1;
    renderPage();
  }
});

nextPageBtn.addEventListener('click', () => {
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  if (pageIndex < totalPages - 1) {
    pageIndex += 1;
    renderPage();
  }
});

closeDetail.addEventListener('click', () => detailModal.classList.add('hidden'));
feedbackClose.addEventListener('click', () => feedbackModal.classList.add('hidden'));

renderPage();
