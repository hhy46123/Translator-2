const translateBtn = document.getElementById('translate-btn');
const saveBtn = document.getElementById('save-btn');
const translatedEl = document.getElementById('translated');
const statusEl = document.getElementById('status');
const textInput = document.getElementById('text');
const directionSelect = document.getElementById('direction');

let lastResponse = null;

async function translate() {
  translatedEl.textContent = '';
  statusEl.textContent = 'Translating...';
  saveBtn.disabled = true;

  const response = await fetch('/api/translate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: textInput.value, direction: directionSelect.value })
  });
  const data = await response.json();
  lastResponse = data;

  translatedEl.textContent = data.translated || 'No results.';
  statusEl.textContent = data.translation_success ? 'Found offline senses.' : 'No offline results.';
  saveBtn.disabled = !(data.translation_success && data.translated);
}

async function saveToNotebook() {
  if (!lastResponse || !lastResponse.translation_success || !lastResponse.translated) {
    statusEl.textContent = 'Nothing to save.';
    return;
  }
  const payload = {
    source_text: lastResponse.source_text,
    translated_text: lastResponse.translated,
    direction: lastResponse.direction,
    senses: lastResponse.senses
  };
  const response = await fetch('/api/notebook/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (response.ok) {
    statusEl.textContent = 'Saved to notebook.';
  } else {
    const error = await response.json();
    statusEl.textContent = error.detail || 'Save failed.';
  }
}

translateBtn.addEventListener('click', translate);
saveBtn.addEventListener('click', saveToNotebook);
textInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    translate();
  }
});
