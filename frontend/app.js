/**
 * NutriGuard AI — Frontend Application Logic
 */

const API_BASE = ''; // Same origin

let _lastParsedProfile = null;

// ============ Utilities ============
async function api(endpoint, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}/api${endpoint}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiMultipart(endpoint, formData) {
  const res = await fetch(`${API_BASE}/api${endpoint}`, { method: 'POST', body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function scrollToApp() { document.getElementById('app').scrollIntoView({ behavior: 'smooth' }); }

function showTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(`tab-${name}`).style.display = 'block';
  btn.classList.add('active');
}

function setStatus(msg) {
  const bar = document.getElementById('statusBar');
  const text = document.getElementById('statusText');
  if (msg) { bar.style.display = 'flex'; text.textContent = msg; } 
  else { bar.style.display = 'none'; }
}

function setLoading(id, loading) {
  const btn = document.getElementById(id);
  if (!btn) return;
  btn.disabled = loading;
  btn.style.opacity = loading ? '0.7' : '1';
}

function showToast(msg, type = 'info') {
  const existing = document.getElementById('toastMsg');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.id = 'toastMsg';
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }, 3500);
}

// FIX: Added missing Tab Switcher
window.switchInputTab = function(tab) {
  document.querySelectorAll('.upload-tab').forEach(el => el.classList.remove('active'));
  
  if (tab === 'upload') {
    document.getElementById('tabUpload').classList.add('active');
    document.getElementById('panelUpload').style.display = 'block';
    document.getElementById('panelText').style.display = 'none';
    document.getElementById('parseBtn').style.display = 'none';
  } else {
    document.getElementById('tabText').classList.add('active');
    document.getElementById('panelUpload').style.display = 'none';
    document.getElementById('panelText').style.display = 'block';
    document.getElementById('parseBtn').style.display = 'flex';
  }
};

// ============ Destination Info ============
let destTimeout;
document.addEventListener('DOMContentLoaded', () => {
  const destInput = document.getElementById('destination');
  if (destInput) {
    destInput.addEventListener('input', () => {
      clearTimeout(destTimeout);
      destTimeout = setTimeout(() => fetchDestInfo(destInput.value), 600);
    });
  }
  loadPrices();
  setupFileUpload();
});

async function fetchDestInfo(dest) {
  if (!dest || dest.length < 2) return;
  try {
    const info = await api(`/destination/${encodeURIComponent(dest)}`);
    const el = document.getElementById('destInfo');
    if (el) {
      el.style.display = 'block';
      el.innerHTML = `🌍 <strong>${info.country}</strong> · ${info.cuisine} Cuisine · <code>${info.language}</code>`;
    }
  } catch (_) {}
}

// ============ File Upload & OCR ============
function setupFileUpload() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('medicalFile');
  if (!dropZone || !fileInput) return;

  dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) handleFileSelected(e.dataTransfer.files[0]);
  });
  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFileSelected(fileInput.files[0]); });
}

function handleFileSelected(file) {
  if (file.size > 10 * 1024 * 1024) { showToast('File too large. Max 10MB.', 'error'); return; }
  document.getElementById('previewFileName').textContent = file.name;
  document.getElementById('previewFileSize').textContent = `${(file.size / 1024).toFixed(1)} KB`;
  document.getElementById('filePreview').style.display = 'flex';
  window._selectedFile = file;
  document.getElementById('ocrBtn').style.display = 'flex';
}

function clearFile() {
  window._selectedFile = null;
  document.getElementById('filePreview').style.display = 'none';
  document.getElementById('ocrBtn').style.display = 'none';
  document.getElementById('medicalFile').value = '';
}

async function uploadAndOCR() {
  const file = window._selectedFile;
  if (!file) { showToast('Select a file first.', 'error'); return; }
  setLoading('ocrBtn', true);
  setStatus('Running Gemini Vision OCR...');
  try {
    const formData = new FormData(); formData.append('file', file);
    const result = await apiMultipart('/ocr', formData);
    if (result.extracted_text) {
      document.getElementById('medicalText').value = result.extracted_text;
      showToast(`✅ OCR complete! Extracted ${result.extracted_text.length} chars`, 'success');
    }
    if (result.parsed_profile) {
      _lastParsedProfile = result.parsed_profile;
      renderProfilePreview(result.parsed_profile);
    }
  } catch (e) { showToast('OCR failed: ' + e.message, 'error'); } 
  finally { setLoading('ocrBtn', false); setStatus(null); }
}

// ============ Parse Profile ============
async function parseMedical() {
  const text = document.getElementById('medicalText').value.trim();
  if (!text) { showToast('Enter medical text first.', 'error'); return; }
  setLoading('parseBtn', true);
  try {
    const result = await api('/parse', 'POST', { text });
    _lastParsedProfile = result;
    renderProfilePreview(result);
  } catch (e) { showToast('Parse failed: ' + e.message, 'error'); } 
  finally { setLoading('parseBtn', false); }
}

function renderProfilePreview(profile) {
  document.getElementById('profilePreview').style.display = 'block';
  const cond = (profile.conditions || []).map(c => `<span class="chip-condition">🩺 ${c}</span>`).join('');
  const allg = (profile.allergies || []).map(a => `<span class="chip-allergy">⚠️ ${a}</span>`).join('');
  const meds = (profile.medications || []).map(m => `<span class="chip-medication">💊 ${m}</span>`).join('');
  document.getElementById('profileContent').innerHTML = `<div class="profile-chips">${cond}${allg}${meds}</div>`;
}

// ============ Full Mission ============
async function runMission() {
  const destination = document.getElementById('destination').value.trim();
  const medicalText = document.getElementById('medicalText').value.trim();
  if (!destination) { showToast('Please enter a destination.', 'error'); return; }

  setLoading('missionBtn', true);
  setStatus('Running multi-agent mission (Health → Nutrition → Travel → Safety)...');

  try {
    const result = await api('/mission', 'POST', {
      user_id: 'user_' + Date.now(),
      destination,
      medical_text: medicalText || null
    });
    if (result.health_profile) _lastParsedProfile = result.health_profile;
    renderMissionResult(result, _lastParsedProfile);
    showToast('✅ Mission complete!', 'success');
  } catch (e) { showToast('Mission failed: ' + e.message, 'error'); } 
  finally { setLoading('missionBtn', false); setStatus(null); }
}

function renderMissionResult(result, profile) {
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('missionResults').style.display = 'block';

  // Risk Header
  const risk = (result.overall_risk || 'Low').toLowerCase();
  const riskEmoji = { critical: '🔴', high: '🔴', moderate: '🟡', low: '🟢' }[risk] || '⚪';
  document.getElementById('riskHeader').className = `risk-header ${risk}`;
  document.getElementById('riskHeader').innerHTML = `<span class="risk-label">${riskEmoji} Overall Risk: ${result.overall_risk}</span>`;

  // Health Tab
  const hp = profile || {};
  document.getElementById('tab-health').innerHTML = `
    <div class="health-summary">${result.health_summary}</div>
  `;

  // Meals Tab
  const meals = result.meal_plan || [];
  document.getElementById('tab-meals').innerHTML = meals.length
    ? meals.map((m, i) => `<div class="meal-card"><div class="meal-num">${i + 1}</div><div class="meal-text">${m}</div></div>`).join('')
    : '<p>No meal plan available.</p>';

  // Risks Tab
  const risksHTML = (result.risks || []).map(r => `<div class="risk-item"><div class="risk-item-text">${r}</div></div>`).join('');
  const actionsHTML = (result.emergency_actions || []).map(a => `<li class="action-item">› ${a}</li>`).join('');
  document.getElementById('tab-risks').innerHTML = `${risksHTML}<div style="margin-top:1rem;"><ul>${actionsHTML}</ul></div>`;

  // Waiter Card Tab
  document.getElementById('tab-card').innerHTML = `
    <div class="waiter-card">
      <div class="card-title">NutriGuard Medical Alert Card</div>
      <div class="translation-text" style="margin-top:1rem;">${result.waiter_card_translation || 'Translation error.'}</div>
    </div>
  `;

  // Hospitals
  const hospitals = result.hospital_recommendations || [];
  document.getElementById('tab-hospitals').innerHTML = hospitals.map(h => {
    const name = typeof h === 'string' ? h : h.name;
    return `<div class="hospital-card">🏥 <b>${name}</b></div>`;
  }).join('');

  document.getElementById('resultsPanel').scrollIntoView({ behavior: 'smooth' });
}

// ============ Query Agent ============
async function runQuery() {
  const query = document.getElementById('queryInput').value.trim();
  if (!query) return;
  const resultEl = document.getElementById('queryResult');
  resultEl.style.display = 'block'; resultEl.textContent = 'Thinking...';
  try {
    const data = await api('/query', 'POST', { query, destination: document.getElementById('destination').value });
    resultEl.textContent = data.response;
  } catch (e) { resultEl.textContent = 'Error: ' + e.message; }
}

async function loadPrices() {
  try {
    const data = await api('/prices');
    if (data.prices) {
      document.getElementById('priceCards').innerHTML = data.prices.slice(0, 4).map(p => `
        <div class="price-card"><b>${p.commodity}</b><br>₹${p.price} (${p.trend})</div>
      `).join('');
    }
  } catch (_) {}
}