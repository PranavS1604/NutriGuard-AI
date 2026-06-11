const API_BASE = '';
let _profile = null; 

// ==========================================
// UTILITIES & MARKDOWN PARSER
// ==========================================
async function apiFetch(endpoint, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
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

window.scrollToApp = function() { document.getElementById('app').scrollIntoView({ behavior: 'smooth' }); }

function setStatus(msg) {
  const bar = document.getElementById('statusBar');
  if (msg) { bar.style.display = 'flex'; document.getElementById('statusText').textContent = msg; } 
  else { bar.style.display = 'none'; }
}

function setBtnLoading(id, loading) {
  const btn = document.getElementById(id);
  if (!btn) return;
  btn.disabled = loading;
  btn.style.opacity = loading ? '0.7' : '1';
}

function parseMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/^### (.*$)/gim, '<div class="md-h3">$1</div>')
    .replace(/^## (.*$)/gim, '<div class="md-h3">$1</div>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^\* (.*$)/gim, '<li>$1</li>')
    .replace(/^- (.*$)/gim, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
  return html;
}

// ==========================================
// TABS & DESTINATION
// ==========================================
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

window.showTab = function (name, btn) {
  document.querySelectorAll('.tab-panel').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.rtab').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-${name}`).style.display = 'block';
  btn.classList.add('active');

  if (name === 'market') fetchMarketPrices();
};

let destTimeout;
document.addEventListener('DOMContentLoaded', () => {
  const destInput = document.getElementById('destination');
  if (destInput) {
    destInput.addEventListener('input', () => {
      clearTimeout(destTimeout);
      destTimeout = setTimeout(() => fetchDestInfo(destInput.value), 600);
    });
  }
  setupDropZone();
});

function getCountryFlag(country) {
  const flags = {
    'Japan': '🇯🇵', 'India': '🇮🇳', 'France': '🇫🇷', 'Italy': '🇮🇹',
    'Mexico': '🇲🇽', 'Thailand': '🇹🇭', 'South Korea': '🇰🇷',
    'United States': '🇺🇸', 'United Kingdom': '🇬🇧', 'China': '🇨🇳',
    'Germany': '🇩🇪', 'Spain': '🇪🇸', 'Australia': '🇦🇺',
    'United Arab Emirates': '🇦🇪', 'Singapore': '🇸🇬', 'Vietnam': '🇻🇳',
  };
  return flags[country] || '🌍';
}

async function fetchDestInfo(dest) {
  if (!dest || dest.length < 2) { document.getElementById('destInfo').style.display = 'none'; return; }
  try {
    const info = await apiFetch(`/destination/${encodeURIComponent(dest)}`);
    const el = document.getElementById('destInfo');
    if (el && info.country !== 'Unknown') {
      el.style.display = 'block';
      const flagEmoji = getCountryFlag(info.country);
      el.innerHTML = `${flagEmoji} <strong>${info.country}</strong> · ${info.cuisine} Cuisine · <code>${info.language}</code>`;
    }
  } catch (_) {}
}

// ==========================================
// UPLOAD & OCR
// ==========================================
function setupDropZone() {
  const dz = document.getElementById('dropZone');
  const fi = document.getElementById('medicalFile');
  if (!dz || !fi) return;

  dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('drag-over'); });
  dz.addEventListener('dragleave', ()  => { dz.classList.remove('drag-over'); });
  dz.addEventListener('drop', e => {
    e.preventDefault(); dz.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  });
  
  dz.addEventListener('click', () => fi.click());
  fi.addEventListener('change', () => { 
    if (fi.files && fi.files.length > 0) {
      handleFile(fi.files[0]); 
    }
  });
}

function handleFile(file) {
  if (file.size > 10 * 1024 * 1024) { alert('File too large. Max 10MB.'); return; }
  window._selectedFile = file;
  
  const nameEl = document.getElementById('previewFileName');
  const sizeEl = document.getElementById('previewFileSize');
  if (nameEl) nameEl.textContent = file.name;
  if (sizeEl) sizeEl.textContent = `${(file.size / 1024).toFixed(1)} KB`;
  
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
  if (!file) { alert('Please select a file first.'); return; }
  
  setBtnLoading('ocrBtn', true); 
  setStatus('Running Vision OCR (Gemini/SambaNova)...');
  
  try {
    const fd = new FormData(); 
    fd.append('file', file);
    const result = await apiMultipart('/ocr', fd);
    
    if (result.extracted_text) {
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

window.parseMedical = async function () {
  const text = (document.getElementById('medicalText').value || '').trim();
  if (!text) { alert('Enter medical text first.'); return; }
  setBtnLoading('parseBtn', true);
  try {
    const result = await apiFetch('/parse', 'POST', { text });
    _profile = result;
    renderProfileChips(result);
  } catch (e) { alert('Parse failed: ' + e.message); } 
  finally { setBtnLoading('parseBtn', false); }
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

// ==========================================
// MISSION EXECUTION & RENDERING
// ==========================================
window.runMission = async function () {
  const destination = (document.getElementById('destination').value || '').trim();
  if (!destination) { alert('Please enter a destination.'); return; }

  setBtnLoading('missionBtn', true);
  setStatus('Running multi-agent mission (Health → Nutrition → Travel → Safety)…');

  try {
    const medicalText = (document.getElementById('medicalText') && document.getElementById('medicalText').value || '').trim();
    const result = await apiFetch('/mission', 'POST', {
      user_id: 'user_' + Date.now(),
      destination,
      medical_text: medicalText || null
    });

    if (result.health_profile) {
      _profile = result.health_profile;
      renderProfileChips(result.health_profile);
    }
    renderMissionResult(result);
  } catch (e) { alert('Mission failed: ' + e.message); } 
  finally { setBtnLoading('missionBtn', false); setStatus(null); }
};

function renderMissionResult(r) {
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('missionResults').style.display = 'block';

  const risk = (r.overall_risk || 'Low').toLowerCase();
  const emoji = { critical: '🔴', high: '🔴', moderate: '🟡', low: '🟢' }[risk] || '⚪';
  const banner = document.getElementById('riskBanner');
  banner.className = `risk-banner ${risk}`;
  banner.innerHTML = `<span>${emoji}</span><span>Overall Risk: <strong>${r.overall_risk}</strong></span>`;

  buildHealthTab(r);
  buildMealsTab(r);
  buildRisksTab(r);

  const lang = (r.destination_info || {}).language || 'en';
  document.getElementById('tab-card').innerHTML = `
    <div class="waiter-card-wrap">
      <div class="waiter-card">
        <div class="wc-header"><div class="wc-header-icon">🛡️</div><div><h3>Medical Alert Card</h3><p>Show this to restaurant staff or medical personnel.</p></div></div>
        <div class="wc-body">
          <div class="wc-lang-badge">🌐 Auto-translated by Gemini/SambaNova · ${lang.toUpperCase()}</div>
          <div class="wc-text">${r.waiter_card_translation || 'Translation unavailable.'}</div>
          <div class="wc-barcode"></div>
        </div>
        <div class="wc-footer">Generated securely via NutriGuard Edge AI</div>
      </div>
    </div>`;

  const hospitals = r.hospital_recommendations || [];
  document.getElementById('tab-hospitals').innerHTML = hospitals.map((h, i) => {
    const name = typeof h === 'string' ? h : (h.name || 'Unknown');
    const address = typeof h === 'object' ? (h.vicinity || h.address || 'Verified Location') : 'Verified Location';
    
    // EXACT REQUESTED GOOGLE MAPS URL FORMAT
    const mapQuery = encodeURIComponent(`${name} ${address}`);
    const mapUrl = `https://www.google.com/maps/search/?api=1&query=${mapQuery}`;
    
    return `
      <div class="hospital-item">
        <div class="hi-icon">🏥</div>
        <div>
          <div class="hi-name">${name}</div>
          <div class="hi-addr">${address}</div>
          <a href="${mapUrl}" target="_blank" rel="noopener" class="hi-link">View on Google Maps →</a>
        </div>
      </div>`;
  }).join('');

  document.getElementById('resultsPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildHealthTab(r) {
  const hp = r.health_profile || {};
  const conds = hp.conditions  || [];
  const allgs = hp.allergies   || [];
  const meds  = hp.medications || [];

  const condHTML = conds.length ? conds.map(c => `<span class="hc-item hc-cond">${c}</span>`).join('') : `<div class="hc-empty">None detected</div>`;
  const allgHTML = allgs.length ? allgs.map(a => `<span class="hc-item hc-allg">${a}</span>`).join('') : `<div class="hc-empty">None detected</div>`;
  const medHTML  = meds.length ? meds.map(m => `<span class="hc-item hc-med">${m}</span>`).join('') : `<div class="hc-empty">None detected</div>`;

  document.getElementById('tab-health').innerHTML = `
    <div class="health-summary-box">
      <strong>🧑‍⚕️ Clinical Overview:</strong><br/> 
      ${r.health_summary || 'No summary available.'}
    </div>
    <div class="health-grid">
      <div class="health-col"><div class="health-col-head">🩺 Conditions</div>${condHTML}</div>
      <div class="health-col"><div class="health-col-head">⚠️ Allergies</div>${allgHTML}</div>
      <div class="health-col"><div class="health-col-head">💊 Medications</div>${medHTML}</div>
    </div>`;
}

function buildMealsTab(r) {
  const meals = r.meal_plan || [];
  
  const formatMeal = (text) => {
    if (text.includes(':')) {
      const parts = text.split(':');
      return `<strong>${parts[0]}:</strong>${parts.slice(1).join(':')}`;
    }
    return text;
  };

  document.getElementById('tab-meals').innerHTML = meals.length
    ? meals.map((m, i) => `
        <div class="meal-item">
          <div class="meal-num">${i + 1}</div>
          <div class="meal-text">${formatMeal(m)}</div>
        </div>`).join('')
    : '<div class="empty-state"><p>No safe meal plan could be generated for this destination.</p></div>';
}

function buildRisksTab(r) {
  const risks = r.risks || [];
  const actions = r.emergency_actions || [];

  const riskHTML = risks.map(risk => {
    let cls = 'sev-normal'; 
    let icon = 'ℹ️';
    const rl = risk.toLowerCase();
    
    if (rl.includes('[critical]') || rl.includes('anaphylaxis') || rl.includes('severe')) {
      cls = 'sev-critical'; icon = '🚨';
    } else if (rl.includes('[high]') || rl.includes('warning')) {
      cls = 'sev-high'; icon = '⚠️';
    } else if (rl.includes('interaction')) {
      icon = '💊';
    }

    const formattedRisk = risk.replace(/(\[.*?\])/, '<strong>$1</strong>');

    return `
      <div class="risk-item ${cls}">
        <div class="risk-icon">${icon}</div>
        <div>${formattedRisk}</div>
      </div>`;
  }).join('') || '<div class="risk-item sev-normal"><div class="risk-icon">✅</div><div>No significant risks identified for this profile.</div></div>';

  const actionsHTML = actions.map(a => `
    <div class="action-item">
      <div class="action-dot">✓</div>
      <div>${a}</div>
    </div>`).join('');

  document.getElementById('tab-risks').innerHTML = `
    ${riskHTML}
    ${actionsHTML ? `
    <div class="actions-section">
      <div class="actions-head">🛡️ Recommended Safety Actions</div>
      ${actionsHTML}
    </div>` : ''}`;
}

// ==========================================
// MARKET PRICES (FIVETRAN)
// ==========================================
async function fetchMarketPrices() {
  const tab = document.getElementById('tab-market');
  tab.innerHTML = `
    <div class="market-header"><h3>📊 Live Agricultural Prices</h3><span class="market-source-badge">⚡ Agmarknet → Fivetran → BigQuery</span></div>
    <div class="market-pipeline"><span class="mp-step mp-active">Agmarknet API</span> <span class="mp-arrow">→</span> <span class="mp-step mp-active">Fivetran</span> <span class="mp-arrow">→</span> <span class="mp-step mp-active">BigQuery</span></div>
    <div id="priceGrid" class="price-grid"><div class="market-loading"><div class="status-spin"></div><span>Fetching live commodity prices…</span></div></div>
    <div class="market-tip">💡 <strong>Fivetran Integration:</strong> Commodity prices are ingested in real-time from India's Agmarknet API via a Fivetran connector and mapped to our DB so agents can give budget-aware meal safety advice.</div>
  `;

  try {
    const data = await apiFetch('/prices');
    if (data.prices && data.prices.length > 0) {
      document.getElementById('priceGrid').innerHTML = data.prices.slice(0, 8).map(p => {
        const icon = { up: '↑', down: '↓', stable: '→' }[p.trend] || '→';
        return `<div class="price-card"><div class="pc-commodity">${p.commodity}</div><div class="pc-price">₹${p.price}</div><div class="pc-unit">per quintal</div><div class="pc-trend ${p.trend}">${icon} ${p.trend.toUpperCase()}</div></div>`;
      }).join('');
    } else {
      document.getElementById('priceGrid').innerHTML = `<div class="market-empty">Live data pipeline currently sleeping.</div>`;
    }
  } catch (e) {
    document.getElementById('priceGrid').innerHTML = `<div class="market-empty">⚠️ Could not load prices.</div>`;
  }
}

// ==========================================
// FLOATING CHAT WIDGET
// ==========================================
window.toggleChat = function() {
  const w = document.getElementById('chatWidget');
  if (w.style.display === 'none') {
    w.style.display = 'flex';
    document.getElementById('queryInput').focus();
  } else {
    w.style.display = 'none';
  }
};

window.runQuery = async function () {
  const input = document.getElementById('queryInput');
  const query = (input.value || '').trim();
  if (!query) return;

  const chatBox = document.getElementById('chatContainer');
  chatBox.innerHTML += `<div class="chat-msg user"><div class="chat-bubble">${escapeHtml(query)}</div></div>`;
  input.value = '';

  const loadId = 'load_' + Date.now();
  chatBox.innerHTML += `<div class="chat-msg ai" id="${loadId}"><div class="chat-bubble loading">Agent is querying Fivetran Data Warehouse…</div></div>`;
  chatBox.scrollTop = chatBox.scrollHeight;

  try {
    const dest = (document.getElementById('destination').value || '').trim();
    const profile = _profile || {};
    const data = await apiFetch('/query', 'POST', {
      query, destination: dest || null,
      conditions: profile.conditions || [],
      allergies: profile.allergies || [],
      medications: profile.medications || []
    });

    const el = document.getElementById(loadId);
    if (el) el.innerHTML = `<div class="chat-bubble">${parseMarkdown(data.response)}</div>`;
  } catch (e) {
    const el = document.getElementById(loadId);
    if (el) el.innerHTML = `<div class="chat-bubble error">Error: ${e.message}</div>`;
  }
  chatBox.scrollTop = chatBox.scrollHeight;
};

function escapeHtml(str) { return String(str).replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>'); }

document.getElementById('queryInput').addEventListener('keydown', e => { if (e.key === 'Enter') window.runQuery(); });