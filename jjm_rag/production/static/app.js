const form = document.querySelector('#query-form');
const input = document.querySelector('#query-input');
const messages = document.querySelector('#messages');
const welcome = document.querySelector('#welcome');
const sendButton = document.querySelector('#send-button');
const sendLabel = document.querySelector('#send-label');
const spinner = document.querySelector('#spinner');
const clearButton = document.querySelector('#clear-button');
const statusDot = document.querySelector('#status-dot');
const statusLabel = document.querySelector('#status-label');
let pendingClarification = null;
const conversationContext = [];

function setStatus(kind, label) {
  statusDot.className = `status-dot ${kind}`;
  statusLabel.textContent = label;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[character]));
}

function renderMarkdown(value, citations = []) {
  const citationNumbers = new Set(citations.map(citation => Number(String(citation.citation_id || '').match(/(\d+)$/)?.[1])).filter(Boolean));
  const inline = text => escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[(\d+)\]/g, (match, number) => citationNumbers.has(Number(number))
      ? `<button type="button" class="citation-link" data-citation="${number}" title="View source and provenance" aria-label="View source ${number}">↗</button>`
      : match);
  const lines = String(value || '').split('\n');
  const rendered = [];
  let listOpen = false;
  const closeList = () => {
    if (listOpen) {
      rendered.push('</ul>');
      listOpen = false;
    }
  };
  lines.forEach(line => {
    if (!line.trim()) {
      closeList();
      return;
    }
    if (line.startsWith('### ')) {
      closeList();
      rendered.push(`<h4>${inline(line.slice(4))}</h4>`);
    } else if (line.startsWith('- ')) {
      if (!listOpen) {
        rendered.push('<ul>');
        listOpen = true;
      }
      rendered.push(`<li>${inline(line.slice(2))}</li>`);
    } else {
      closeList();
      rendered.push(`<p>${inline(line)}</p>`);
    }
  });
  closeList();
  return rendered.join('');
}

function addUserMessage(text) {
  const node = document.createElement('article');
  node.className = 'message user';
  node.innerHTML = `<div class="message-label">You</div><div class="message-body">${escapeHtml(text)}</div>`;
  messages.append(node);
}

function citationDetail(citation) {
  const location = citation.page ? `Page ${citation.page}` : citation.record_id ? `Record ${citation.record_id}` : citation.source_type || 'Retrieved evidence';
  const provenance = citation.provenance_id ? `Provenance ${citation.provenance_id}` : 'Provenance unavailable';
  const number = Number(String(citation.citation_id || '').match(/(\d+)$/)?.[1]) || 0;
  return `<div class="source" id="source-evidence-${number}"><strong>${escapeHtml(citation.filename || 'Unnamed source')}</strong><small>${escapeHtml(location)} · ${escapeHtml(provenance)}</small></div>`;
}

function addAssistantMessage(response) {
  const grounded = response.confidence?.grounded === true;
  const level = response.confidence?.level || 'unknown';
  const citations = Array.isArray(response.citations) ? response.citations : [];
  const sources = citations.length ? `<div class="sources">${citations.map(citationDetail).join('')}</div>` : '';
  const status = grounded ? `<span class="badge">Grounded · ${escapeHtml(level)}</span>` : `<span class="badge abstain">Insufficient evidence</span>`;
  const retrieval = response.retrieval || {};
  const channels = Array.isArray(retrieval.channels) ? retrieval.channels.join(', ') : 'none';
  const node = document.createElement('article');
  node.className = 'message assistant';
  const clarification = response.clarification;
  node.innerHTML = `<div class="message-label">JJM RAG</div><div class="message-body">${renderMarkdown(response.answer || 'No answer returned.', citations)}</div><div class="meta-row">${status}<span>${escapeHtml(retrieval.route || 'unknown')} route</span><span>${escapeHtml(String(response.confidence?.evidence_count ?? 0))} evidence items</span><span>${escapeHtml(channels)}</span></div>${sources}`;
  messages.append(node);
  node.querySelectorAll('.citation-link').forEach(button => {
    button.addEventListener('click', () => {
      const target = node.querySelector(`#source-evidence-${button.dataset.citation}`);
      if (!target) return;
      target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      target.classList.add('source-highlight');
      window.setTimeout(() => target.classList.remove('source-highlight'), 1400);
    });
  });
  if (clarification) {
    pendingClarification = { originalQuestion: response.retrieval?.original_query || conversationContext.at(-1) || '', required: clarification.required || [] };
    if (Array.isArray(clarification.options) && clarification.options.length) {
      const choices = document.createElement('div');
      choices.className = 'clarification-options';
      clarification.options.forEach(option => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'clarification-choice';
        button.textContent = option;
        button.addEventListener('click', () => askQuestion(option));
        choices.append(button);
      });
      node.querySelector('.message-body').after(choices);
    }
  } else pendingClarification = null;
}

function addError(message) {
  const node = document.createElement('div');
  node.className = 'error-box';
  node.textContent = message;
  messages.append(node);
}

async function checkHealth() {
  try {
    const response = await fetch('/ready');
    const data = await response.json();
    if (response.ok && data.status === 'ready') setStatus('ready', 'Service ready');
    else setStatus('error', 'Service degraded');
  } catch (_) {
    setStatus('error', 'Service unavailable');
  }
}

async function askQuestion(question) {
  const originalQuestion = question;
  // Source-choice options are physical filenames.  Always use the API's
  // explicit marker rather than display wording such as "source/report";
  // otherwise a clicked option is treated as a new question and can repeat
  // the same clarification indefinitely.
  const required = pendingClarification?.required || [];
  const selectedField = required.includes('source/report') || required.includes('source') ? 'source' : (required.join(' or ') || 'detail');
  const composedQuestion = pendingClarification?.originalQuestion ? `${pendingClarification.originalQuestion}\nSelected ${selectedField}: ${question}` : question;
  addUserMessage(originalQuestion);
  welcome.hidden = true;
  sendButton.disabled = true;
  spinner.hidden = false;
  sendLabel.textContent = 'Querying corpus';
  try {
    conversationContext.push(composedQuestion);
    const response = await fetch('/api/v1/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: composedQuestion, context: conversationContext.slice(-6) }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'The RAG service could not answer this request.');
    addAssistantMessage(payload);
  } catch (error) {
    addError(error.message || 'The RAG service could not be reached.');
  } finally {
    sendButton.disabled = false;
    spinner.hidden = true;
    sendLabel.textContent = 'Send question';
    input.focus();
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question || sendButton.disabled) return;
  input.value = '';
  askQuestion(question);
});

input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

clearButton.addEventListener('click', () => {
  messages.replaceChildren();
  pendingClarification = null;
  conversationContext.length = 0;
  welcome.hidden = false;
  input.value = '';
  input.focus();
});

checkHealth();
