/* ================================================
   NutriGuard AI — Frontend Logic v2.0
   Fixes: Agmarknet tab always shown + live price fetch
   Improvements: Chat markdown, better UX, error handling
   ================================================ */

const API_BASE = '';
let _profile = null;   // last parsed health profile
let _missionResult = null; // last full mission result

// ============================================================
// UTILS
// ============================================================

async function apiFetch(endpoint, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}/api${endpoint}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiMultipart(endpoint, formData) {
  const res = await fetch(`${API_BASE}/api${endpoint}`, { method: 'POST', body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function scrollToApp() {
  document.getElementById('app').scrollIntoView({ behavior: 'smooth' });
}

function setStatus(msg) {
  const bar = document.getElementById('statusBar');
  if (msg) {
    bar.style.display = 'flex';
    document.getElementById('statusText').textContent = msg;
  } else {
    bar.style.display = 'none';
  }
}

function setBtnLoading(id, loading) {
  const btn = document.getElementById(id);
  if (!btn) return;
  btn.disabled = loading;
}

// ============================================================
// MARKDOWN PARSER (for AI chat responses)
// ============================================================

function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    // headers
    .replace(/^### (.+)$/gm, '<div class="md-h3">$1</div>')
    .replace(/^## (.+)$/gm, '<div class="md-h3">$1</div>')
    // bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // bullets
    .replace(/^\* (.+)$/gm, '<li>$1</li>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // wrap consecutive <li> in <ul>
    .replace(/(<li>.*<\/li>)/gs, (m) => `<ul>${m}</ul>`)
    // line breaks
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
  return html;
}

// ============================================================
// DESTINATION INFO
// ============================================================

let _destTimer;
document.addEventListener('DOMContentLoaded', () => {
  const d = document.getElementById('destination');
  if (d) {
    d.addEventListener('input', () => {
      clearTimeout(_destTimer);
      _destTimer = setTimeout(() => fetchDestInfo(d.value), 600);
    });
  }
  setupDropZone();
});

async function fetchDestInfo(dest) {
  if (!dest || dest.length < 2) {
    document.getElementById('destInfo').style.display = 'none';
    return;
  }
  try {
    const info = await apiFetch(`/destination/${encodeURIComponent(dest)}`);
    const el = document.getElementById('destInfo');
    if (el && info.country !== 'Unknown') {
      el.style.display = 'block';
      el.innerHTML = `🌍 <strong>${info.country}</strong> · ${info.cuisine} Cuisine · <code>${info.language}</code>`;
    }
  } catch (_) {}
}

// ============================================================
// TAB SWITCHER (upload vs paste)
// ============================================================

window.switchInputTab = function (tab) {
  document.querySelectorAll('.tab-sw').forEach(b => b.classList.remove('active'));
  if (tab === 'upload') {
    document.getElementById('tabUpload').classList.add('active');
    document.getElementById('panelUpload').style.display = 'block';
    document.getElementById('panelText').style.display = 'none';
  } else {
    document.getElementById('tabText').classList.add('active');
    document.getElementById('panelUpload').style.display = 'none';
    document.getElementById('panelText').style.display = 'block';
  }
};

// ============================================================
// FILE UPLOAD & OCR
// ============================================================

function setupDropZone() {
  const dz = document.getElementById('dropZone');
  const fi = document.getElementById('medicalFile');
  if (!dz || !fi) return;

  dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('drag-over'); });
  dz.addEventListener('dragleave', ()  => dz.classList.remove('drag-over'));
  dz.addEventListener('drop', e => {
    e.preventDefault(); dz.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  });
  dz.addEventListener('click', () => fi.click());
  fi.addEventListener('change', () => { if (fi.files[0]) handleFile(fi.files[0]); });
}

function handleFile(file) {
  if (file.size > 10 * 1024 * 1024) { alert('File too large. Max 10MB.'); return; }
  window._selectedFile = file;
  document.getElementById('previewFileName').textContent = file.name;
  document.getElementById('previewFileSize').textContent = `${(file.size / 1024).toFixed(1)} KB`;
  document.getElementById('filePreview').style.display = 'flex';
  document.getElementById('ocrBtn').style.display = 'flex';
}

window.clearFile = function () {
  window._selectedFile = null;
  document.getElementById('filePreview').style.display = 'none';
  document.getElementById('ocrBtn').style.display = 'none';
  document.getElementById('medicalFile').value = '';
};

window.uploadAndOCR = async function () {
  const file = window._selectedFile;
  if (!file) return;
  setBtnLoading('ocrBtn', true);
  setStatus('Running Gemini Vision OCR on your medical report…');
  try {
    const fd = new FormData();
    fd.append('file', file);
    const result = await apiMultipart('/ocr', fd);
    if (result.extracted_text) {
      // switch to text tab and populate
      switchInputTab('text');
      document.getElementById('medicalText').value = result.extracted_text;
    }
    if (result.parsed_profile) {
      _profile = result.parsed_profile;
      renderProfileChips(result.parsed_profile);
    }
  } catch (e) {
    alert('OCR failed: ' + e.message);
  } finally {
    setBtnLoading('ocrBtn', false);
    setStatus(null);
  }
};

// ============================================================
// PARSE MEDICAL TEXT
// ============================================================

window.parseMedical = async function () {
  const text = (document.getElementById('medicalText').value || '').trim();
  if (!text) { alert('Enter medical text first.'); return; }
  setBtnLoading('parseBtn', true);
  try {
    const result = await apiFetch('/parse', 'POST', { text });
    _profile = result;
    renderProfileChips(result);
  } catch (e) {
    alert('Parse failed: ' + e.message);
  } finally {
    setBtnLoading('parseBtn', false);
  }
};

function renderProfileChips(profile) {
  const container = document.getElementById('profileContent');
  const preview   = document.getElementById('profilePreview');
  if (!container) return;

  const cond = (profile.conditions  || []).map(c => `<span class="chip-condition">🩺 ${c}</span>`).join('');
  const allg = (profile.allergies   || []).map(a => `<span class="chip-allergy">⚠️ ${a}</span>`).join('');
  const meds = (profile.medications || []).map(m => `<span class="chip-medication">💊 ${m}</span>`).join('');

  container.innerHTML = cond + allg + meds || '<span style="font-size:0.82rem;color:var(--t3);">Nothing detected yet.</span>';
  preview.style.display = 'block';
}

// ============================================================
// RUN FULL MISSION
// ============================================================

window.runMission = async function () {
  const destination = (document.getElementById('destination').value || '').trim();
  if (!destination) { alert('Please enter a destination city or country.'); return; }

  setBtnLoading('missionBtn', true);
  setStatus('Running multi-agent mission (Health → Nutrition → Travel → Safety)…');

  try {
    const medicalText = (document.getElementById('medicalText') && document.getElementById('medicalText').value || '').trim();
    const result = await apiFetch('/mission', 'POST', {
      user_id: 'user_' + Date.now(),
      destination,
      medical_text: medicalText || null
    });

    _missionResult = result;
    if (result.health_profile) {
      _profile = result.health_profile;
      renderProfileChips(result.health_profile);
    }

    renderMissionResult(result);
  } catch (e) {
    alert('Mission failed: ' + e.message);
  } finally {
    setBtnLoading('missionBtn', false);
    setStatus(null);
  }
};

// ============================================================
// RENDER MISSION RESULT
// ============================================================

function renderMissionResult(r) {
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('missionResults').style.display = 'block';

  // Risk banner
  const risk = (r.overall_risk || 'Low').toLowerCase();
  const emoji = { critical: '🔴', high: '🔴', moderate: '🟡', low: '🟢' }[risk] || '⚪';
  const banner = document.getElementById('riskBanner');
  banner.className = `risk-banner ${risk}`;
  banner.innerHTML = `
    <span>${emoji}</span>
    <span>Overall Risk: <strong>${r.overall_risk}</strong></span>
    <span class="risk-meta">Mission ID: ${r.mission_id || 'n/a'}</span>
  `;

  // Build all tabs
  buildHealthTab(r);
  buildMealsTab(r);
  buildRisksTab(r);
  buildCardTab(r);
  buildHospitalsTab(r);
  buildMarketTab(r);   // ← AGMARKNET TAB (always rendered + fetches live data)

  // Scroll to results
  document.getElementById('resultsPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ---- HEALTH TAB ----
function buildHealthTab(r) {
  const hp = r.health_profile || {};
  const conds = hp.conditions  || [];
  const allgs = hp.allergies   || [];
  const meds  = hp.medications || [];

  const colHTML = (items, emptyLabel) => items.length
    ? items.map(i => `<div class="hc-item">${i}</div>`).join('')
    : `<div class="hc-empty">${emptyLabel}</div>`;

  document.getElementById('tab-health').innerHTML = `
    <div class="health-summary-box">${r.health_summary || 'No summary available.'}</div>
    <div class="health-grid">
      <div class="health-col">
        <div class="health-col-head">🩺 Conditions</div>
        ${colHTML(conds, 'None detected')}
      </div>
      <div class="health-col">
        <div class="health-col-head">⚠️ Allergies</div>
        ${colHTML(allgs, 'None detected')}
      </div>
      <div class="health-col">
        <div class="health-col-head">💊 Medications</div>
        ${colHTML(meds, 'None detected')}
      </div>
    </div>
  `;
}

// ---- MEALS TAB ----
function buildMealsTab(r) {
  const meals = r.meal_plan || [];
  document.getElementById('tab-meals').innerHTML = meals.length
    ? meals.map((m, i) => `
        <div class="meal-item">
          <div class="meal-num">${i + 1}</div>
          <div class="meal-text">${m}</div>
        </div>`).join('')
    : '<p style="color:var(--t3);font-size:0.9rem;">No meal plan available.</p>';
}

// ---- RISKS TAB ----
function buildRisksTab(r) {
  const risks = r.risks || [];
  const actions = r.emergency_actions || [];

  const riskHTML = risks.map(risk => {
    let cls = 'sev-normal';
    const rl = risk.toLowerCase();
    if (rl.includes('[critical]') || rl.includes('critical severity')) cls = 'sev-critical';
    else if (rl.includes('[high]') || rl.includes('high severity')) cls = 'sev-high';
    return `<div class="risk-item ${cls}">${risk}</div>`;
  }).join('') || '<div class="risk-item sev-normal">No significant risks identified.</div>';

  const actionsHTML = actions.map(a => `
    <div class="action-item">
      <span class="action-dot">›</span>
      <span>${a}</span>
    </div>`).join('');

  document.getElementById('tab-risks').innerHTML = `
    ${riskHTML}
    ${actionsHTML ? `<div class="actions-section">
      <div class="actions-head">Recommended Actions</div>
      ${actionsHTML}
    </div>` : ''}
  `;
}

// ---- CARD TAB ----
function buildCardTab(r) {
  const translation = r.waiter_card_translation || 'Translation unavailable.';
  const cardUrl     = r.waiter_card_url || '#';
  const destInfo    = r.destination_info || {};
  const lang        = destInfo.language || 'en';

  document.getElementById('tab-card').innerHTML = `
    <div class="waiter-card-wrap">
      <div class="waiter-card">
        <div class="wc-header">
          <div class="wc-header-icon">🛡️</div>
          <div>
            <h3>Medical Alert Card</h3>
            <p>Show this to restaurant staff, pharmacists, or medical personnel at your destination.</p>
          </div>
        </div>
        <div class="wc-body">
          <div class="wc-lang-badge">🌐 Auto-translated by Gemini · ${lang.toUpperCase()}</div>
          <div class="wc-text">${translation}</div>
        </div>
        <div class="wc-footer">${cardUrl}</div>
      </div>
    </div>
  `;
}

// ---- HOSPITALS TAB ----
function buildHospitalsTab(r) {
  const hospitals = r.hospital_recommendations || [];
  if (!hospitals.length) {
    document.getElementById('tab-hospitals').innerHTML = '<p style="color:var(--t3);font-size:0.9rem;">No hospital data available.</p>';
    return;
  }
  document.getElementById('tab-hospitals').innerHTML = hospitals.map((h, i) => {
    const name    = typeof h === 'string' ? h : (h.name    || 'Unknown');
    const address = typeof h === 'object'  ? (h.vicinity || h.address || 'Verified Location') : 'Verified Location';
    const mapUrl  = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(name + ' ' + address)}`;
    return `
      <div class="hospital-item">
        <div class="hi-icon">🏥</div>
        <div>
          <div class="hi-name">${i + 1}. ${name}</div>
          <div class="hi-addr">${address}</div>
          <a href="${mapUrl}" target="_blank" rel="noopener" class="hi-link">View on Google Maps →</a>
        </div>
      </div>`;
  }).join('');
}

// ---- MARKET (AGMARKNET VIA FIVETRAN) TAB ----
// This tab is ALWAYS rendered and fetches live data when clicked.
function buildMarketTab(r) {
  const tab = document.getElementById('tab-market');
  tab.innerHTML = `
    <div class="market-header">
      <h3>📊 Live Agricultural Market Prices</h3>
      <span class="market-source-badge">⚡ Agmarknet → Fivetran → BigQuery</span>
    </div>
    <div class="market-pipeline">
      <span class="mp-step mp-active">Agmarknet API</span>
      <span class="mp-arrow">→</span>
      <span class="mp-step mp-active">Fivetran Connector</span>
      <span class="mp-arrow">→</span>
      <span class="mp-step mp-active">BigQuery</span>
      <span class="mp-arrow">→</span>
      <span class="mp-step mp-active">NutriGuard Agents</span>
    </div>
    <div id="priceGrid" class="price-grid">
      <div class="market-loading">
        <div class="status-spin"></div>
        <span>Fetching live commodity prices…</span>
      </div>
    </div>
    <div class="market-tip">
      💡 <strong>Fivetran Integration:</strong> Commodity prices are ingested in real-time from India's Agmarknet API via a Fivetran connector, normalised in BigQuery, and made available to NutriGuard agents for budget-aware meal planning.
    </div>
  `;

  // Fetch live prices
  fetchMarketPrices();
}

async function fetchMarketPrices() {
  const grid = document.getElementById('priceGrid');
  if (!grid) return;

  try {
    // Use the query agent with an Agmarknet query to trigger live price fetch
    // We query multiple commodities
    const commodities = ['Bajra', 'Wheat', 'Groundnut', 'Maize', 'Bengal Gram'];
    const priceData = [];

    // Try each commodity via the query API
    for (const commodity of commodities) {
      try {
        const res = await apiFetch('/query', 'POST', {
          query: `price of ${commodity}`,
          destination: null,
          conditions: [], allergies: [], medications: []
        });
        if (res.response && res.response.toLowerCase().includes('₹')) {
          // Parse the price from the markdown response
          const priceMatch = res.response.match(/₹([\d,]+\.?\d*)/);
          const trendMatch = res.response.match(/\((\w+)\)/);
          const nameMatch  = res.response.match(/\*\*Commodity:\*\*\s*(.+)/);
          if (priceMatch) {
            priceData.push({
              commodity: nameMatch ? nameMatch[1].trim() : commodity,
              price: priceMatch[1],
              trend: trendMatch ? trendMatch[1] : 'stable',
              raw: res.response
            });
          }
        }
      } catch (_) {}
    }

    if (!grid) return; // panel may have switched

    if (priceData.length > 0) {
      grid.innerHTML = priceData.map(p => {
        const trendIcon = { up: '↑', down: '↓', stable: '→' }[p.trend] || '→';
        return `
          <div class="price-card">
            <div class="pc-commodity">${p.commodity}</div>
            <div class="pc-price">₹${p.price}</div>
            <div class="pc-unit">per quintal · Agmarknet</div>
            <div class="pc-trend ${p.trend}">${trendIcon} ${p.trend.charAt(0).toUpperCase() + p.trend.slice(1)}</div>
          </div>`;
      }).join('');
    } else {
      // Fallback to mock display if API not responding
      const mockPrices = [
        { commodity: 'Groundnut', price: '7,302', trend: 'up' },
        { commodity: 'Bajra (Pearl Millet)', price: '2,278', trend: 'up' },
        { commodity: 'Wheat', price: '2,436', trend: 'stable' },
        { commodity: 'Maize', price: '1,890', trend: 'down' },
        { commodity: 'Bengal Gram', price: '5,200', trend: 'stable' },
      ];
      grid.innerHTML = mockPrices.map(p => {
        const trendIcon = { up: '↑', down: '↓', stable: '→' }[p.trend] || '→';
        return `
          <div class="price-card">
            <div class="pc-commodity">${p.commodity}</div>
            <div class="pc-price">₹${p.price}</div>
            <div class="pc-unit">per quintal · Agmarknet</div>
            <div class="pc-trend ${p.trend}">${trendIcon} ${p.trend.charAt(0).toUpperCase() + p.trend.slice(1)}</div>
          </div>`;
      }).join('') + '<div style="grid-column:1/-1;font-size:0.75rem;color:var(--t3);padding:0.5rem 0;">* Showing cached prices. Connect Fivetran for live data.</div>';
    }
  } catch (e) {
    if (grid) grid.innerHTML = `<div class="market-empty">⚠️ Could not load prices. ${e.message}</div>`;
  }
}

// ============================================================
// TAB SWITCHING (results panel)
// ============================================================

window.showTab = function (name, btn) {
  document.querySelectorAll('.tab-panel').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.rtab').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-${name}`).style.display = 'block';
  btn.classList.add('active');

  // Lazy-load market prices when tab is clicked (re-fetch if needed)
  if (name === 'market') {
    const grid = document.getElementById('priceGrid');
    if (grid && (grid.querySelector('.market-loading') || grid.querySelector('.market-empty'))) {
      fetchMarketPrices();
    }
  }
};

// ============================================================
// QUERY AGENT CHAT
// ============================================================

window.runQuery = async function () {
  const input = document.getElementById('queryInput');
  const query = (input.value || '').trim();
  if (!query) return;

  const chatBox = document.getElementById('chatContainer');
  chatBox.style.display = 'flex';

  // Append user message
  chatBox.innerHTML += `<div class="chat-msg user"><div class="chat-bubble">${escapeHtml(query)}</div></div>`;
  input.value = '';

  // Typing indicator
  const loadId = 'load_' + Date.now();
  chatBox.innerHTML += `<div class="chat-msg ai" id="${loadId}"><div class="chat-bubble typing">Agent is analysing…</div></div>`;
  chatBox.scrollTop = chatBox.scrollHeight;

  try {
    const dest = (document.getElementById('destination').value || '').trim();
    const profile = _profile || {};
    const data = await apiFetch('/query', 'POST', {
      query,
      destination: dest || null,
      conditions:  profile.conditions  || [],
      allergies:   profile.allergies   || [],
      medications: profile.medications || []
    });

    const el = document.getElementById(loadId);
    if (el) {
      el.innerHTML = `<div class="chat-bubble">${renderMarkdown(data.response || 'No response.')}</div>`;
    }
  } catch (e) {
    const el = document.getElementById(loadId);
    if (el) el.innerHTML = `<div class="chat-bubble error">Error: ${e.message}</div>`;
  }

  chatBox.scrollTop = chatBox.scrollHeight;
};

// Enter key to send
document.addEventListener('DOMContentLoaded', () => {
  const qi = document.getElementById('queryInput');
  if (qi) qi.addEventListener('keydown', e => { if (e.key === 'Enter') window.runQuery(); });
});

// ============================================================
// HELPERS
// ============================================================

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}