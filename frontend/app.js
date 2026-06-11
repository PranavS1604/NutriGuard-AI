/**
 * NutriGuard AI — Frontend Application Logic
 * Talks to the FastAPI backend at /api/*
 */

const API_BASE = '';  // Same origin — backend serves frontend

// Global state
let _lastParsedProfile = null;

// ============ Utilities ============

async function api(endpoint, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}/api${endpoint}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiMultipart(endpoint, formData) {
  const res = await fetch(`${API_BASE}/api${endpoint}`, {
    method: 'POST',
    body: formData  // No Content-Type header — browser sets it with boundary
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function scrollToApp() {
  document.getElementById('app').scrollIntoView({ behavior: 'smooth' });
}

function showTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(`tab-${name}`).style.display = 'block';
  btn.classList.add('active');
}

function setStatus(msg) {
  const bar = document.getElementById('statusBar');
  const text = document.getElementById('statusText');
  if (msg) {
    bar.style.display = 'flex';
    text.textContent = msg;
  } else {
    bar.style.display = 'none';
  }
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

// ============ Destination Info ============

let destTimeout;
document.addEventListener('DOMContentLoaded', () => {
  const destInput = document.getElementById('destination');
  if (destInput) {
    destInput.addEventListener('input', () => {
      clearTimeout(destTimeout);
      destTimeout = setTimeout(() => fetchDestInfo(destInput.value), 600);
    });
    fetchDestInfo(destInput.value);  // On load
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
      const flagEmoji = getCountryFlag(info.country);
      el.innerHTML = `${flagEmoji} <strong>${info.country}</strong> · ${info.cuisine} Cuisine · <code>${info.language}</code>`;
    }
  } catch (_) {}
}

function getCountryFlag(country) {
  const flags = {
    'Japan': '🇯🇵', 'India': '🇮🇳', 'France': '🇫🇷', 'Italy': '🇮🇹',
    'Mexico': '🇲🇽', 'Thailand': '🇹🇭', 'South Korea': '🇰🇷',
    'United States': '🇺🇸', 'United Kingdom': '🇬🇧', 'China': '🇨🇳',
    'Germany': '🇩🇪', 'Spain': '🇪🇸', 'Australia': '🇦🇺',
    'United Arab Emirates': '🇦🇪', 'Singapore': '🇸🇬', 'Vietnam': '🇻🇳',
    'Indonesia': '🇮🇩', 'Brazil': '🇧🇷', 'Greece': '🇬🇷', 'Turkey': '🇹🇷',
    'Morocco': '🇲🇦', 'Canada': '🇨🇦', 'Portugal': '🇵🇹', 'Switzerland': '🇨🇭',
    'Netherlands': '🇳🇱', 'Malaysia': '🇲🇾', 'Philippines': '🇵🇭', 'Argentina': '🇦🇷'
  };
  return flags[country] || '🌍';
}

// ============ File Upload Setup ============

function setupFileUpload() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('medicalFile');
  if (!dropZone || !fileInput) return;

  // Drag and drop
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
  });
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelected(file);
  });

  // Click to browse
  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFileSelected(fileInput.files[0]);
  });
}

function handleFileSelected(file) {
  const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'application/pdf'];
  if (!allowed.includes(file.type) && !file.name.match(/\.(jpg|jpeg|png|webp|pdf)$/i)) {
    showToast('Please upload a JPG, PNG, WEBP, or PDF file.', 'error');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast('File too large. Maximum 10MB allowed.', 'error');
    return;
  }

  // Show preview
  const preview = document.getElementById('filePreview');
  const previewImg = document.getElementById('previewImg');
  const previewName = document.getElementById('previewFileName');
  const previewSize = document.getElementById('previewFileSize');

  previewName.textContent = file.name;
  previewSize.textContent = `${(file.size / 1024).toFixed(1)} KB`;

  if (file.type.startsWith('image/')) {
    previewImg.src = URL.createObjectURL(file);
    previewImg.style.display = 'block';
  } else {
    previewImg.style.display = 'none';
  }
  preview.style.display = 'flex';

  // Store file reference for upload
  window._selectedFile = file;
  document.getElementById('ocrBtn').style.display = 'flex';
}

function clearFile() {
  window._selectedFile = null;
  document.getElementById('filePreview').style.display = 'none';
  document.getElementById('ocrBtn').style.display = 'none';
  document.getElementById('medicalFile').value = '';
  const previewImg = document.getElementById('previewImg');
  if (previewImg.src) URL.revokeObjectURL(previewImg.src);
  previewImg.src = '';
}

// ============ OCR Upload ============

async function uploadAndOCR() {
  const file = window._selectedFile;
  if (!file) { showToast('Please select a file first.', 'error'); return; }

  setLoading('ocrBtn', true);
  setStatus('Running Gemini Vision OCR on your medical document...');

  try {
    const formData = new FormData();
    formData.append('file', file);

    const result = await apiMultipart('/ocr', formData);

    // Show extracted text in the textarea
    const textarea = document.getElementById('medicalText');
    if (result.extracted_text && result.extracted_text.length > 10) {
      textarea.value = result.extracted_text;
      showToast(`✅ OCR complete! Extracted ${result.extracted_text.length} characters (${Math.round(result.confidence_score * 100)}% confidence)`, 'success');
    }

    // If parsed_profile is available, render it
    if (result.parsed_profile) {
      _lastParsedProfile = result.parsed_profile;
      renderProfilePreview(result.parsed_profile);
    }

    setStatus(null);
  } catch (e) {
    setStatus(null);
    showToast('OCR failed: ' + e.message, 'error');
  } finally {
    setLoading('ocrBtn', false);
  }
}

// ============ Parse Medical Profile ============

async function parseMedical() {
  const text = document.getElementById('medicalText').value.trim();
  if (!text) { showToast('Please enter medical text first.', 'error'); return; }

  setLoading('parseBtn', true);
  try {
    const result = await api('/parse', 'POST', { text });
    _lastParsedProfile = result;
    renderProfilePreview(result);
  } catch (e) {
    showToast('Parse failed: ' + e.message, 'error');
  } finally {
    setLoading('parseBtn', false);
  }
}

function renderProfilePreview(profile) {
  const preview = document.getElementById('profilePreview');
  const content = document.getElementById('profileContent');
  preview.style.display = 'block';

  const conditions = (profile.conditions || []).map(c => `<span class="chip-condition">🩺 ${c}</span>`).join('');
  const allergies = (profile.allergies || []).map(a => `<span class="chip-allergy">⚠️ ${a}</span>`).join('');
  const meds = (profile.medications || []).map(m => `<span class="chip-medication">💊 ${m}</span>`).join('');
  const riskClass = { High: 'high', Moderate: 'moderate', Low: 'low' }[profile.risk_level] || 'low';

  const hasData = conditions || allergies || meds;

  content.innerHTML = `
    <div class="profile-chips">
      ${hasData
        ? `${conditions}${allergies}${meds}<span class="risk-badge ${riskClass}">Risk: ${profile.risk_level || 'Low'}</span>`
        : `<span style="color:var(--text-muted); font-size:0.85rem;">No medical data detected. Try providing more detail.</span>`
      }
    </div>
  `;
}

// ============ Run Full Mission ============

async function runMission() {
  const destination = document.getElementById('destination').value.trim();
  const medicalText = document.getElementById('medicalText').value.trim();

  if (!destination) { showToast('Please enter a destination.', 'error'); return; }

  setLoading('missionBtn', true);
  setStatus('Initializing multi-agent mission...');

  try {
    // Step 1: Parse medical text if provided and not yet parsed
    let profile = _lastParsedProfile;
    if (medicalText && !profile) {
      setStatus('Extracting health profile with Gemini AI...');
      try {
        profile = await api('/parse', 'POST', { text: medicalText });
        _lastParsedProfile = profile;
        renderProfilePreview(profile);
      } catch (_) {}
    }

    // Step 2: Run full mission
    setStatus('Running multi-agent mission (Health → Nutrition → Travel → Safety)...');
    const result = await api('/mission', 'POST', {
      user_id: 'user_' + Date.now(),
      destination,
      medical_text: medicalText || null
    });

    // Use health_profile from mission result if available (more accurate - used actual text)
    if (result.health_profile) {
      _lastParsedProfile = result.health_profile;
      renderProfilePreview(result.health_profile);
      profile = result.health_profile;
    }

    setStatus(null);
    renderMissionResult(result, profile);
    showToast('✅ Mission complete!', 'success');

  } catch (e) {
    setStatus(null);
    showToast('Mission failed: ' + e.message, 'error');
  } finally {
    setLoading('missionBtn', false);
  }
}

// ============ Render Mission Result ============

function renderMissionResult(result, profile) {
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('missionResults').style.display = 'block';

  // Use profile from mission result or passed profile
  const hp = result.health_profile || profile || {};
  const destInfo = result.destination_info || {};

  // Risk Header
  const risk = (result.overall_risk || 'Low').toLowerCase();
  const riskEmoji = { critical: '🔴', moderate: '🟡', low: '🟢' }[risk] || '⚪';
  const riskHeader = document.getElementById('riskHeader');
  riskHeader.className = `risk-header ${risk}`;
  riskHeader.innerHTML = `
    <span class="risk-label">${riskEmoji} Overall Risk: ${result.overall_risk}</span>
    <span class="risk-meta">${destInfo.country || document.getElementById('destination').value} · ${destInfo.cuisine || ''} Cuisine</span>
  `;

  // --- Tab: Health ---
  const cond = hp.conditions || [];
  const allergy = hp.allergies || [];
  const meds = hp.medications || [];
  document.getElementById('tab-health').innerHTML = `
    <div class="health-grid">
      <div class="health-col">
        <div class="health-col-title">🩺 Conditions</div>
        ${cond.length ? cond.map(c => `<div class="health-item">${c}</div>`).join('') : '<div class="health-item" style="color:var(--text-muted)">None detected</div>'}
      </div>
      <div class="health-col">
        <div class="health-col-title">⚠️ Allergies</div>
        ${allergy.length ? allergy.map(a => `<div class="health-item" style="color:#fca5a5">${a}</div>`).join('') : '<div class="health-item" style="color:var(--text-muted)">None detected</div>'}
      </div>
      <div class="health-col">
        <div class="health-col-title">💊 Medications</div>
        ${meds.length ? meds.map(m => `<div class="health-item">${m}</div>`).join('') : '<div class="health-item" style="color:var(--text-muted)">None detected</div>'}
      </div>
    </div>
    <div class="health-summary">${result.health_summary || 'Health analysis complete.'}</div>
  `;

  // --- Tab: Meals ---
  const meals = result.meal_plan || [];
  document.getElementById('tab-meals').innerHTML = meals.length
    ? meals.map((m, i) => `<div class="meal-card"><div class="meal-num">${i + 1}</div><div class="meal-text">${m}</div></div>`).join('')
    : '<p style="color:var(--text-muted)">No meal plan available for this destination.</p>';

  // --- Tab: Risks ---
  const risks = result.risks || [];
  const actions = result.emergency_actions || [];

  const categorizeRisk = r => {
    if (r.includes('[Critical]')) return 'critical';
    if (r.includes('[High]') || r.includes('[High Severity]') || r.includes('Severity]')) return 'high';
    return 'normal';
  };

  const risksHTML = risks.map(r => {
    const cat = categorizeRisk(r);
    const labelMap = { critical: '⚠️ Critical Interaction', high: '⚠️ High Risk', normal: 'ℹ️ Advisory' };
    return `<div class="risk-item ${cat}">
      <div class="risk-item-label">${labelMap[cat]}</div>
      <div class="risk-item-text">${r}</div>
    </div>`;
  }).join('');

  const actionsHTML = actions.map(a => `<li class="action-item"><span class="action-bullet">›</span>${a}</li>`).join('');

  document.getElementById('tab-risks').innerHTML = `
    ${risksHTML || '<p style="color:var(--text-muted)">No specific risks identified.</p>'}
    <div style="margin-top:1.25rem;">
      <div class="health-col-title" style="margin-bottom:0.75rem;">📋 Emergency Actions</div>
      <ul class="actions-list">${actionsHTML}</ul>
    </div>
  `;

  // --- Tab: Waiter Card ---
  const destination = document.getElementById('destination').value;
  const destCountry = destInfo.country || destination;
  const destLang = destInfo.language || 'en';

  // Use the Gemini-translated text from backend, or fallback to English
  const translatedText = result.waiter_card_translation ||
    'I have strict medical dietary requirements. I cannot consume foods containing my allergens. ' +
    'Please inform the chef and ensure my food is prepared safely. Thank you for your assistance.';

  const langNames = {
    'ja': 'Japanese', 'hi': 'Hindi', 'fr': 'French', 'it': 'Italian',
    'es': 'Spanish', 'th': 'Thai', 'ko': 'Korean', 'zh': 'Chinese',
    'de': 'German', 'ar': 'Arabic', 'pt': 'Portuguese', 'vi': 'Vietnamese',
    'id': 'Indonesian', 'nl': 'Dutch', 'el': 'Greek', 'tr': 'Turkish',
    'ms': 'Malay', 'tl': 'Filipino', 'ta': 'Tamil', 'te': 'Telugu',
    'bn': 'Bengali', 'en': 'English'
  };
  const langName = langNames[destLang] || destLang.toUpperCase();

  const riskLevel = hp.risk_level || 'Low';
  const riskBadgeClass = { High: 'high', Moderate: 'moderate', Low: 'low' }[riskLevel] || 'low';

  document.getElementById('tab-card').innerHTML = `
    <div class="waiter-card">
      <div class="card-header">
        <div class="card-logo">🛡️</div>
        <div>
          <div class="card-title">NutriGuard Medical Alert Card</div>
          <div class="card-subtitle">Show this to waiters, doctors, and emergency services in ${destCountry}</div>
        </div>
        <span class="risk-badge ${riskBadgeClass}" style="margin-left:auto;">Risk: ${riskLevel}</span>
      </div>
      ${cond.length || allergy.length ? `
      <div class="card-section">
        <div class="card-section-label">Medical Conditions &amp; Allergies</div>
        <div class="card-section-value">${[...cond, ...allergy].join(' · ') || 'Not specified'}</div>
      </div>` : ''}
      ${meds.length ? `
      <div class="card-section">
        <div class="card-section-label">Active Medications</div>
        <div class="card-section-value">${meds.join(' · ')}</div>
      </div>` : ''}
      <div class="card-translation">
        <div class="translation-label">
          ${result.waiter_card_translation ? `🌐 Auto-Translated to ${langName}` : '📝 Standard Medical Alert'}
        </div>
        <div class="translation-text">${translatedText}</div>
      </div>
      ${result.waiter_card_url && !result.waiter_card_url.includes('mock') ? `
      <div class="card-url">🔗 ${result.waiter_card_url}</div>` : ''}
    </div>
  `;

  // --- Tab: Hospitals ---
  const hospitals = result.hospital_recommendations || [];
  const destAdvisories = result.destination_advisories || [];

  document.getElementById('tab-hospitals').innerHTML = hospitals.length
    ? hospitals.map((h, i) => {
        // h can be a string (hospital name) or object
        const name = typeof h === 'string' ? h : (h.name || h.toString());
        const vicinity = typeof h === 'object' ? h.vicinity || '' : '';
        const rating = typeof h === 'object' && h.rating ? `⭐ ${h.rating}` : '';
        return `
        <div class="hospital-card">
          <div class="hospital-num">🏥</div>
          <div>
            <div class="hospital-name">${name}</div>
            <div class="hospital-meta">${vicinity || `Near ${destCountry}`} ${rating}</div>
          </div>
        </div>`;
      }).join('') + `
      <div class="health-summary" style="margin-top:0.75rem;">
        ${destAdvisories.length
          ? `⚠️ Travel Advisories: ${destAdvisories.join(' · ')}`
          : '✅ No specific travel advisories for this destination.'}
        ${!result.hospital_recommendations.some(h => typeof h === 'object' && h.rating)
          ? '<br><small style="color:var(--text-muted)">Set <code>GOOGLE_MAPS_API_KEY</code> for real-time verified hospital data.</small>'
          : ''}
      </div>`
    : '<p style="color:var(--text-muted)">No hospitals found for this destination.</p>';

  // Scroll to results
  document.getElementById('resultsPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============ Query Agent ============

async function runQuery() {
  const query = document.getElementById('queryInput').value.trim();
  if (!query) return;

  const btn = document.querySelector('.btn-icon');
  btn.disabled = true;
  btn.textContent = '...';

  const resultEl = document.getElementById('queryResult');
  resultEl.style.display = 'block';
  resultEl.textContent = 'Thinking...';

  try {
    const dest = document.getElementById('destination').value;
    // Use last parsed profile for allergies/medications context
    const profile = _lastParsedProfile || {};
    const data = await api('/query', 'POST', {
      query,
      destination: dest || null,
      allergies: profile.allergies || [],
      medications: profile.medications || []
    });
    resultEl.textContent = data.response;
  } catch (e) {
    resultEl.textContent = 'Error: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = '→';
  }
}

// Allow Enter key in query input
document.addEventListener('DOMContentLoaded', () => {
  const qi = document.getElementById('queryInput');
  if (qi) qi.addEventListener('keydown', e => { if (e.key === 'Enter') runQuery(); });
});

// ============ Load Live Prices ============

async function loadPrices() {
  try {
    const data = await api('/prices');
    const container = document.getElementById('priceCards');
    if (!container) return;

    if (data.prices && data.prices.length > 0) {
      const trendIcon = t => t === 'up' ? '↑' : t === 'down' ? '↓' : '→';
      container.innerHTML = data.prices.slice(0, 8).map(p => `
        <div class="price-card">
          <div class="price-commodity">${p.commodity}</div>
          <div class="price-value">₹${Number(p.price).toLocaleString('en-IN')}</div>
          <div class="price-trend ${p.trend}">${trendIcon(p.trend)} ${p.trend}</div>
        </div>
      `).join('');
    } else {
      container.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem; text-align:center; width:100%; padding:1rem;">Live price data loading — Agmarknet → Fivetran → BigQuery pipeline active</p>';
    }
  } catch (_) {
    const c = document.getElementById('priceCards');
    if (c) c.innerHTML = '';
  }
}
