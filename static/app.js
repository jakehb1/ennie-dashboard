/* ── Ennie Support Dashboard — app.js ──────────────────────────────────────── */

// ── Toast notifications ──────────────────────────────────────────────────────
function toast(message, type) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = message;
  el.className   = 'toast' + (type ? ' toast-' + type : '');
  void el.offsetWidth; // reflow
  el.classList.add('show');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('show'), 3000);
}

// ── API helpers ──────────────────────────────────────────────────────────────
async function apiPost(url, data) {
  const r = await fetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(data || {}),
  });
  return r.json();
}

async function apiGet(url) {
  const r = await fetch(url);
  return r.json();
}

async function apiPut(url, data) {
  const r = await fetch(url, {
    method:  'PUT',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(data || {}),
  });
  return r.json();
}

async function apiDelete(url) {
  const r = await fetch(url, { method: 'DELETE' });
  return r.json();
}

// ── Modal helpers ────────────────────────────────────────────────────────────
function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('active');
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('active');
}

// Close modal when clicking overlay background
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
  }
});

// Escape key closes all modals
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.active')
            .forEach(m => m.classList.remove('active'));
  }
});

// ── Inbox — draft card removal ───────────────────────────────────────────────
function removeDraftCard(id) {
  const card = document.querySelector('[data-draft-id="' + id + '"]');
  if (!card) return;
  card.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
  card.style.opacity    = '0';
  card.style.transform  = 'translateX(16px)';
  setTimeout(() => {
    card.remove();
    // Update subtitle count
    const list = document.querySelector('.draft-list');
    const remaining = list ? list.querySelectorAll('.draft-card').length : 0;
    const sub = document.querySelector('.page-subtitle');
    if (sub) {
      sub.textContent = remaining + ' pending draft' + (remaining !== 1 ? 's' : '') + ' awaiting review';
    }
    // Show empty state if none left
    if (remaining === 0 && list) {
      list.innerHTML = '<div class="glass-card empty-state">'
        + '<div class="empty-state-icon">✓</div>'
        + '<h3>All clear!</h3><p>No pending drafts in your inbox.</p></div>';
    }
  }, 210);
}

// ── Approve ──────────────────────────────────────────────────────────────────
function approveDraft(id) {
  apiPost('/api/drafts/' + id + '/approve').then(res => {
    if (res.ok) { removeDraftCard(id); toast('Draft approved', 'success'); }
    else        { toast('Something went wrong', 'error'); }
  }).catch(() => toast('Network error', 'error'));
}

// ── Reject ───────────────────────────────────────────────────────────────────
function rejectDraft(id) {
  const m = document.getElementById('reject-modal');
  if (!m) return;
  m.dataset.draftId = id;
  document.getElementById('reject-notes').value = '';
  openModal('reject-modal');
}

function confirmReject() {
  const m  = document.getElementById('reject-modal');
  const id = m.dataset.draftId;
  const notes = document.getElementById('reject-notes').value;
  apiPost('/api/drafts/' + id + '/reject', { notes }).then(res => {
    if (res.ok) { removeDraftCard(id); toast('Draft rejected'); closeModal('reject-modal'); }
    else        { toast('Something went wrong', 'error'); }
  });
}

// ── Escalate (Jakeh / Casey / Charlie) ───────────────────────────────────────────────────────
const ESCALATION_NAMES = { jakeh: 'Jakeh', casey: 'Casey', charlie: 'Charlie' };

function escalateDraft(id) {
  const m = document.getElementById('escalate-modal');
  if (!m) return;
  m.dataset.draftId = id;
  document.getElementById('escalate-notes').value = '';
  document.getElementById('escalate-to').value = 'jakeh';
  openModal('escalate-modal');
}

function confirmEscalate() {
  const m  = document.getElementById('escalate-modal');
  const id = m.dataset.draftId;
  const to = document.getElementById('escalate-to').value;
  const notes = document.getElementById('escalate-notes').value;
  const name = ESCALATION_NAMES[to] || to;
  apiPost('/api/drafts/' + id + '/escalate', { to, notes }).then(res => {
    if (res.ok) { removeDraftCard(id); toast('Escalated to ' + name); closeModal('escalate-modal'); }
    else        { toast('Something went wrong', 'error'); }
  });
}

// ── Edit + Approve ───────────────────────────────────────────────────────────
function editDraft(id) {
  const card    = document.querySelector('[data-draft-id="' + id + '"]');
  const preview = card ? card.querySelector('.draft-preview') : null;
  const m       = document.getElementById('edit-modal');
  if (!m) return;
  m.dataset.draftId = id;
  document.getElementById('edit-draft-text').value = preview ? preview.textContent.trim() : '';
  openModal('edit-modal');
}

function confirmEdit() {
  const m  = document.getElementById('edit-modal');
  const id = m.dataset.draftId;
  const draft_text = document.getElementById('edit-draft-text').value.trim();
  if (!draft_text) { toast('Draft text required', 'error'); return; }
  apiPost('/api/drafts/' + id + '/edit', { draft_text }).then(res => {
    if (res.ok) { removeDraftCard(id); toast('Edited and approved', 'success'); closeModal('edit-modal'); }
    else        { toast('Something went wrong', 'error'); }
  });
}

// ── Contact Lookup ───────────────────────────────────────────────────────────
async function doLookup() {
  const email = (document.getElementById('lookup-email') || {}).value;
  if (!email || !email.trim()) return;

  const resultsEl = document.getElementById('lookup-results');
  if (!resultsEl) return;
  resultsEl.innerHTML = '<div style="text-align:center;padding:48px;"><div class="spinner"></div></div>';

  try {
    const data = await apiGet('/api/lookup?email=' + encodeURIComponent(email.trim()));
    if (data.error) {
      resultsEl.innerHTML = '<p class="text-muted text-sm" style="padding:16px;">' + esc(data.error) + '</p>';
      return;
    }
    renderLookupResults(data);
  } catch (_) {
    resultsEl.innerHTML = '<p class="text-muted text-sm" style="padding:16px;">Lookup failed — check your connection.</p>';
  }
}

function renderLookupResults(data) {
  const el = document.getElementById('lookup-results');
  if (!el) return;
  const { kajabi, eventbrite, klaviyo } = data;

  let html = '<div class="lookup-results">';

  // Kajabi
  html += '<div class="glass-card lookup-card">';
  html += '<div class="lookup-card-title"><span>🏛</span> Kajabi</div>';
  if (kajabi.found) {
    html += row('Name',        esc(kajabi.name || '—'));
    html += row('Logins',      esc(kajabi.logins || '—'));
    html += row('Last active', esc(kajabi.last_active || '—'));
    if (kajabi.offers && kajabi.offers.length) {
      html += row('Offers', tagList(kajabi.offers));
    }
    if (kajabi.tags && kajabi.tags.length) {
      html += row('Tags', tagList(kajabi.tags));
    }
  } else {
    html += '<p class="not-found">' + esc(kajabi.summary || 'Not found') + '</p>';
  }
  html += '</div>';

  // Eventbrite
  html += '<div class="glass-card lookup-card">';
  html += '<div class="lookup-card-title"><span>🎫</span> Eventbrite</div>';
  if (eventbrite.found && eventbrite.orders.length) {
    eventbrite.orders.forEach(order => {
      html += '<div style="padding:9px 0;border-bottom:1px solid rgba(0,0,0,0.05);">';
      html += '<div style="font-size:13px;font-weight:600;">' + esc(order.event_name) + '</div>';
      html += '<div style="font-size:12px;color:var(--gray);margin-top:3px;display:flex;align-items:center;gap:5px;">';
      html += esc(order.event_date) + ' · ' + esc(order.ticket_type);
      html += ' · <span class="status-dot status-' + esc(order.status) + '"></span> ' + esc(order.status);
      html += '</div></div>';
    });
  } else {
    html += '<p class="not-found">' + esc(eventbrite.summary || 'No orders found') + '</p>';
  }
  html += '</div>';

  // Klaviyo
  html += '<div class="glass-card lookup-card">';
  html += '<div class="lookup-card-title"><span>📧</span> Klaviyo</div>';
  if (klaviyo.found) {
    html += row('Name',       esc(klaviyo.name || '—'));
    html += row('Subscribed', esc(klaviyo.created || '—'));
    if (klaviyo.lists && klaviyo.lists.length) {
      html += row('Lists', tagList(klaviyo.lists));
    }
  } else {
    html += '<p class="not-found">' + esc(klaviyo.summary || 'Not found') + '</p>';
  }
  html += '</div>';

  html += '</div>';
  el.innerHTML = html;
}

function row(key, val) {
  return '<div class="lookup-row"><span class="lookup-key">' + key
       + '</span><span class="lookup-val">' + val + '</span></div>';
}

function tagList(items) {
  return '<div class="tag-list">'
       + items.map(i => '<span class="tag">' + esc(i) + '</span>').join('')
       + '</div>';
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Lookup — Enter key
const lookupInput = document.getElementById('lookup-email');
if (lookupInput) {
  lookupInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doLookup();
  });
}

// ── Escalation — respond ─────────────────────────────────────────────────────
function respondToEscalation(id) {
  const m = document.getElementById('respond-modal');
  if (!m) return;
  m.dataset.escId = id;
  document.getElementById('respond-text').value = '';
  openModal('respond-modal');
}

function confirmRespond() {
  const m        = document.getElementById('respond-modal');
  const id       = m.dataset.escId;
  const response = document.getElementById('respond-text').value.trim();
  if (!response) { toast('Response required', 'error'); return; }
  apiPost('/api/escalations/' + id + '/respond', { response }).then(res => {
    if (res.ok) {
      toast('Response saved', 'success');
      closeModal('respond-modal');
      setTimeout(() => location.reload(), 420);
    } else {
      toast('Something went wrong', 'error');
    }
  });
}

// ── Escalation — Re-escalate ────────────────────────────────────────
function reEscalate(id) {
  const sel = document.getElementById('re-escalate-to-' + id);
  const to = sel ? sel.value : 'jakeh';
  const m = document.getElementById('re-escalate-modal');
  if (!m) return;
  m.dataset.escId = id;
  m.dataset.escalateTo = to;
  const name = ESCALATION_NAMES[to] || to;
  document.getElementById('re-escalate-title').textContent = 'Re-escalate to ' + name;
  document.getElementById('re-escalate-notes').value = '';
  openModal('re-escalate-modal');
}

function confirmReEscalate() {
  const m     = document.getElementById('re-escalate-modal');
  const id    = m.dataset.escId;
  const to    = m.dataset.escalateTo;
  const notes = document.getElementById('re-escalate-notes').value;
  const name  = ESCALATION_NAMES[to] || to;
  apiPost('/api/escalations/' + id + '/re-escalate', { to, notes }).then(res => {
    if (res.ok) {
      toast('Re-escalated to ' + name);
      closeModal('re-escalate-modal');
      setTimeout(() => location.reload(), 420);
    } else {
      toast('Something went wrong', 'error');
    }
  });
}

// ── Knowledge Base ───────────────────────────────────────────────────────────
function openAddKB() {
  document.getElementById('kb-modal-title').textContent = 'Add Knowledge Base Entry';
  document.getElementById('kb-edit-id').value  = '';
  document.getElementById('kb-topic').value    = '';
  document.getElementById('kb-question').value = '';
  document.getElementById('kb-answer').value   = '';
  openModal('kb-modal');
}

function editKBEntry(id, topic, question, answer) {
  document.getElementById('kb-modal-title').textContent = 'Edit Knowledge Base Entry';
  document.getElementById('kb-edit-id').value  = id;
  document.getElementById('kb-topic').value    = topic;
  document.getElementById('kb-question').value = question;
  document.getElementById('kb-answer').value   = answer;
  openModal('kb-modal');
}

async function submitKB() {
  const id       = document.getElementById('kb-edit-id').value;
  const topic    = document.getElementById('kb-topic').value.trim();
  const question = document.getElementById('kb-question').value.trim();
  const answer   = document.getElementById('kb-answer').value.trim();

  if (!topic || !question || !answer) {
    toast('All fields are required', 'error');
    return;
  }

  let res;
  if (id) {
    res = await apiPut('/api/kb/' + id, { topic, question, answer });
  } else {
    res = await apiPost('/api/kb', { topic, question, answer });
  }

  if (res.ok) {
    toast(id ? 'Entry updated' : 'Entry added', 'success');
    closeModal('kb-modal');
    setTimeout(() => location.reload(), 420);
  } else {
    toast(res.error || 'Something went wrong', 'error');
  }
}

async function deleteKBEntry(id) {
  if (!confirm('Delete this knowledge base entry?')) return;
  const res = await apiDelete('/api/kb/' + id);
  if (res.ok) {
    const el = document.getElementById('kb-' + id);
    if (el) {
      el.style.transition = 'opacity 0.18s ease';
      el.style.opacity    = '0';
      setTimeout(() => el.remove(), 200);
    }
    toast('Entry deleted');
  } else {
    toast('Something went wrong', 'error');
  }
}

// ── Global Search ─────────────────────────────────────────────────────────────────
(function() {
  const input = document.getElementById('global-search');
  const dropdown = document.getElementById('search-results');
  if (!input || !dropdown) return;

  let debounce = null;

  input.addEventListener('input', function() {
    clearTimeout(debounce);
    const q = this.value.trim();
    if (q.length < 2) { dropdown.classList.remove('active'); return; }
    debounce = setTimeout(() => doSearch(q), 250);
  });

  input.addEventListener('focus', function() {
    if (this.value.trim().length >= 2 && dropdown.innerHTML) dropdown.classList.add('active');
  });

  document.addEventListener('click', function(e) {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.remove('active');
    }
  });

  input.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { dropdown.classList.remove('active'); this.blur(); }
  });

  async function doSearch(q) {
    try {
      const res = await apiGet('/api/search?q=' + encodeURIComponent(q));
      if (!res.results) { dropdown.classList.remove('active'); return; }

      let html = '';
      if (res.count > 0) {
        html += '<div class="search-count">' + res.count + ' result' + (res.count !== 1 ? 's' : '') + '</div>';
        res.results.forEach(function(r) {
          const date = (r.created_at || '').substring(0, 10);
          html += '<div class="search-result" onclick="window.location=\'/?\'">';
          html += '<div class="search-result-sender">' + esc(r.from_name || r.from_email || 'Unknown') + '</div>';
          html += '<div class="search-result-subject">' + esc(r.subject || 'No subject') + '</div>';
          html += '<div class="search-result-meta">';
          html += '<span>' + esc(r.from_email || '') + '</span>';
          html += '<span>·</span>';
          html += '<span>' + date + '</span>';
          if (r.status) html += '<span class="search-result-status">' + esc(r.status) + '</span>';
          html += '</div></div>';
        });
      } else {
        html = '<div class="search-empty">No results for \u201c' + esc(q) + '\u201d</div>';
      }

      dropdown.innerHTML = html;
      dropdown.classList.add('active');
    } catch (e) {
      dropdown.innerHTML = '<div class="search-empty">Search error</div>';
      dropdown.classList.add('active');
    }
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }
})();
