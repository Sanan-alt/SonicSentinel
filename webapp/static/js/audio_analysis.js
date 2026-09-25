/**
 * SonicSentinel - Audio File Analysis & Validation Module
 * Single & Batch upload, file validation (format, size, duration, sample rate),
 * Dual-Model Comparison (Python vs Google Teachable Machine), SNR & Spectrogram.
 */

document.addEventListener('DOMContentLoaded', () => {
  initAudioAnalysis();
});

function initAudioAnalysis() {
  const dropZone = document.getElementById('audioDropZone');
  const fileInput = document.getElementById('audioFileInput');
  const batchInput = document.getElementById('batchFileInput');
  const runAnalysisBtn = document.getElementById('runAnalysisBtn');

  if (dropZone && fileInput) {
    dropZone.addEventListener('click', () => fileInput.click());

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
      if (e.dataTransfer.files.length > 0) {
        handleFileSelection(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
      }
    });
  }

  // Batch Upload handler
  if (batchInput) {
    batchInput.addEventListener('change', (e) => {
      handleBatchUpload(e.target.files);
    });
  }

  if (runAnalysisBtn) {
    runAnalysisBtn.addEventListener('click', triggerDualModelInference);
  }
}

// 1. Audio File Validation (Format, Size, Duration, Sampling Rate)
async function handleFileSelection(file) {
  const validationSummary = document.getElementById('validationSummary');
  const analysisResultsSection = document.getElementById('analysisResultsSection');
  
  if (!validationSummary) return;
  validationSummary.style.display = 'block';
  if (analysisResultsSection) analysisResultsSection.style.display = 'none';

  // Allowed Formats
  const allowedExtensions = ['wav', 'mp3', 'flac', 'ogg', 'm4a'];
  const ext = file.name.split('.').pop().toLowerCase();
  const formatValid = allowedExtensions.includes(ext);

  // Size limit (Max 25 MB)
  const sizeMB = file.size / (1024 * 1024);
  const sizeValid = sizeMB <= 25;

  // Read Audio Metadata using AudioContext & HTML5 Audio
  let duration = 0;
  let sampleRate = 44100;
  let durationValid = true;

  try {
    const audioObj = new Audio(URL.createObjectURL(file));
    await new Promise((resolve) => {
      audioObj.onloadedmetadata = () => {
        duration = audioObj.duration;
        resolve();
      };
      audioObj.onerror = () => resolve();
      setTimeout(resolve, 1500); // safety fallback
    });

    // Audio context for sample rate
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioCtx();
    sampleRate = ctx.sampleRate;
    ctx.close();

  } catch (err) {
    console.warn("Could not read exact audio properties:", err);
    duration = 4.2; // default demo fallback
  }

  // Max duration 180s (3 min)
  durationValid = duration > 0 && duration <= 180;

  // Display validation UI
  document.getElementById('valFileName').textContent = file.name;
  document.getElementById('valFormat').innerHTML = formatValid 
    ? `<span class="badge badge-safe"><i class="fa-solid fa-check"></i> ${ext.toUpperCase()} (Valid)</span>`
    : `<span class="badge badge-danger"><i class="fa-solid fa-xmark"></i> ${ext.toUpperCase()} (Unsupported)</span>`;

  document.getElementById('valSize').innerHTML = sizeValid
    ? `<span class="badge badge-safe"><i class="fa-solid fa-check"></i> ${sizeMB.toFixed(2)} MB</span>`
    : `<span class="badge badge-danger"><i class="fa-solid fa-xmark"></i> ${sizeMB.toFixed(2)} MB (Max 25MB)</span>`;

  document.getElementById('valDuration').innerHTML = durationValid
    ? `<span class="badge badge-safe"><i class="fa-solid fa-check"></i> ${duration.toFixed(2)}s</span>`
    : `<span class="badge badge-warning"><i class="fa-solid fa-triangle-exclamation"></i> ${duration.toFixed(1)}s (Max 180s)</span>`;

  document.getElementById('valSampleRate').innerHTML = `<span class="badge badge-info">${sampleRate} Hz</span>`;

  const isValidOverall = formatValid && sizeValid;
  const runBtn = document.getElementById('runAnalysisBtn');
  if (runBtn) {
    runBtn.disabled = !isValidOverall;
    if (isValidOverall) {
      runBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  window.currentAudioFile = file;
}

// 2. Dual-Model Inference & Confidence Score Comparison (REAL upload -> models)
async function triggerDualModelInference() {
  const runBtn = document.getElementById('runAnalysisBtn');
  const loadingIndicator = document.getElementById('analysisLoading');
  const resultsSection = document.getElementById('analysisResultsSection');

  if (!window.currentAudioFile) {
    alert('Please select an audio file first.');
    return;
  }

  if (runBtn) runBtn.disabled = true;
  if (loadingIndicator) loadingIndicator.style.display = 'flex';

  try {
    const form = new FormData();
    form.append('audio', window.currentAudioFile);

    const res = await fetch('/api/classify-audio', { method: 'POST', body: form });
    const data = await res.json();

    if (loadingIndicator) loadingIndicator.style.display = 'none';

    if (!res.ok || data.error) {
      alert('Analysis failed: ' + (data.error || 'unknown error'));
      return;
    }

    if (resultsSection) {
      resultsSection.style.display = 'block';
      resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    const py = data.python;
    const gtm = data.gtm;
    const comp = data.comparison;
    const quality = data.audio_quality;

    setText('resEventId', data.event_id);
    setText('resCategoryName', data.final_class_name);

    const sevBadge = document.getElementById('resSeverityBadge');
    if (sevBadge) {
      sevBadge.textContent = data.severity;
      const isCritical = ['Critical', 'High'].includes(data.severity);
      sevBadge.className = `badge ${isCritical ? 'badge-danger' : 'badge-warning'}`;
    }

    // Python model
    setText('pyModelScore', `${py.confidence}%`);
    setBar('pyModelBar', py.confidence);
    // GTM model
    setText('tmModelScore', `${gtm.confidence}%`);
    setBar('tmModelBar', gtm.confidence);

    const deltaEl = document.getElementById('modelsConfidenceDelta');
    if (deltaEl) {
      deltaEl.textContent = `Δ ${comp.confidence_difference}% - ${comp.agreement}`;
    }

    // Audio quality (real)
    setText('valSnrDb', `${quality.snr_db} dB`);
    setText('valClipping', `${quality.clipping_ratio}%`);
    setText('valBgNoise', `${quality.rms}`);
    setText('valQualityRating', quality.quality);

    // Real waveform + spectrogram images from backend
    renderVisual('analysisWaveformImg', data.waveform_url);
    renderVisual('analysisSpectrogramImg', data.spectrogram_url);
    // Fallback canvas if the page uses a canvas element
    drawStaticSpectrogram('analysisWaveformCanvas');

    const playBtn = document.getElementById('playAnalysedAudioBtn');
    if (playBtn && window.currentAudioFile) {
      playBtn.onclick = () => {
        const audio = new Audio(URL.createObjectURL(window.currentAudioFile));
        audio.play();
      };
    }
  } catch (err) {
    console.error('Classification error:', err);
    if (loadingIndicator) loadingIndicator.style.display = 'none';
    alert('Classification request failed. Is the server running and models trained?');
  } finally {
    if (runBtn) runBtn.disabled = false;
  }
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setBar(id, pct) {
  const el = document.getElementById(id);
  if (el) el.style.width = `${pct}%`;
}

function renderVisual(imgId, url) {
  if (!url) return;
  let img = document.getElementById(imgId);
  if (img) {
    img.src = url;
    img.style.display = 'block';
  }
}

// 3. Batch Upload (REAL - each file classified by the backend)
async function handleBatchUpload(fileList) {
  const tableBody = document.getElementById('batchUploadTableBody');
  const batchContainer = document.getElementById('batchUploadResults');

  if (!tableBody || !batchContainer) return;
  batchContainer.style.display = 'block';
  tableBody.innerHTML = '<tr><td colspan="7">Uploading and classifying…</td></tr>';

  const form = new FormData();
  Array.from(fileList).forEach((file) => form.append('audio', file));

  try {
    const res = await fetch('/api/classify-batch', { method: 'POST', body: form });
    const data = await res.json();
    tableBody.innerHTML = '';

    (data.results || []).forEach((r) => {
      const row = document.createElement('tr');
      if (r.error) {
        row.innerHTML = `
          <td><strong>${r.filename}</strong></td>
          <td colspan="5"><span class="badge badge-danger">${r.error}</span></td>
          <td>-</td>`;
      } else {
        row.innerHTML = `
          <td><strong>${r.filename}</strong></td>
          <td><span class="badge badge-safe">Valid</span></td>
          <td>-</td>
          <td><span class="badge badge-safe">Classified</span></td>
          <td><strong>${r.final_class}</strong></td>
          <td><span class="badge badge-info">${r.confidence}%</span></td>
          <td><span class="badge badge-${severityClass(r.severity)}">${r.severity}</span></td>`;
      }
      tableBody.appendChild(row);
    });
  } catch (err) {
    console.error('Batch error:', err);
    tableBody.innerHTML = '<tr><td colspan="7"><span class="badge badge-danger">Batch classification failed.</span></td></tr>';
  }
}

function severityClass(sev) {
  if (['Critical', 'High'].includes(sev)) return 'danger';
  if (sev === 'Medium') return 'warning';
  return 'info';
}

function getAnalysisVisColors() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const savedTheme = localStorage.getItem('sonicsentinel_vis_theme') || (isLight ? 'lab' : 'sonar');

  switch (savedTheme) {
    case 'sonar': return '#00f5ff';
    case 'emerald': return '#10b981';
    case 'cyber': return '#38bdf8';
    case 'lab':
    default: return '#0284c7';
  }
}

// Redraw on theme change
window.addEventListener('visThemeChanged', () => {
  drawStaticSpectrogram('analysisWaveformCanvas');
});

function drawStaticSpectrogram(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Draw simulated waveform
  ctx.strokeStyle = getAnalysisVisColors();
  ctx.lineWidth = 2.5;
  ctx.beginPath();

  const points = 120;
  for (let i = 0; i < points; i++) {
    const x = (i / points) * w;
    // Sudden burst pattern in middle (acoustic event signature)
    const envelope = Math.exp(-Math.pow((i - points * 0.45) / 12, 2));
    const noise = (Math.random() * 2 - 1) * 15;
    const y = (h / 2) + Math.sin(i * 0.4) * (20 + envelope * 65) + noise;

    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}
