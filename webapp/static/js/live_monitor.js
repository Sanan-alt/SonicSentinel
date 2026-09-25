/**
 * SonicSentinel - Live Microphone Monitoring Station
 * Implements Web Audio API microphone stream, 5 status states, oscilloscope,
 * frequency spectrogram and real-time acoustic event classification.
 */

let audioContext = null;
let mediaStream = null;
let analyser = null;
let animationFrameId = null;
let isPaused = false;
let liveBusy = false;          // prevents overlapping classification requests
let scriptNode = null;         // ScriptProcessor capturing raw PCM
let pcmChunks = [];            // buffered Float32 PCM for the current window
let liveSampleRate = 44100;
let windowTimer = null;        // interval that classifies each fixed window
const WINDOW_MS = 2500;        // fixed live window length (SRS: 1-3s)

// Encode buffered Float32 PCM chunks into a 16-bit PCM WAV Blob.
function encodeWav(chunks, sampleRate) {
  let length = 0;
  for (const c of chunks) length += c.length;
  const pcm = new Float32Array(length);
  let off = 0;
  for (const c of chunks) { pcm.set(c, off); off += c.length; }

  const buffer = new ArrayBuffer(44 + pcm.length * 2);
  const view = new DataView(buffer);
  const writeStr = (o, s) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };

  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + pcm.length * 2, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);            // PCM
  view.setUint16(22, 1, true);            // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);           // 16-bit
  writeStr(36, 'data');
  view.setUint32(40, pcm.length * 2, true);

  let p = 44;
  for (let i = 0; i < pcm.length; i++) {
    const s = Math.max(-1, Math.min(1, pcm[i]));
    view.setInt16(p, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    p += 2;
  }
  return new Blob([view], { type: 'audio/wav' });
}

// Take the current PCM window, encode to WAV, send to the backend for a real
// dual-model classification, and reflect the result live.
async function processLiveWindow() {
  if (isPaused || liveBusy || pcmChunks.length === 0) return;
  const chunks = pcmChunks;
  pcmChunks = [];                          // start a fresh window

  // Ignore near-silent windows (nothing meaningful to classify).
  let peak = 0;
  for (const c of chunks) for (let i = 0; i < c.length; i++) peak = Math.max(peak, Math.abs(c[i]));
  if (peak < 0.01) return;

  liveBusy = true;
  try {
    const wav = encodeWav(chunks, liveSampleRate);
    const form = new FormData();
    form.append('audio', wav, 'live_window.wav');
    const res = await fetch('/api/classify-live', { method: 'POST', body: form });
    const data = await res.json();
    if (res.ok && !data.error) {
      updateLiveResult(data);
    }
  } catch (err) {
    console.error('Live classification failed:', err);
  } finally {
    liveBusy = false;
  }
}

// 5 Required States: 'Available', 'Active', 'Paused', 'Disconnected', 'Permission denied'
let currentMicStatus = 'Disconnected';

document.addEventListener('DOMContentLoaded', () => {
  initLiveMonitor();
});

function initLiveMonitor() {
  const startBtn = document.getElementById('startMicBtn');
  const pauseBtn = document.getElementById('pauseMicBtn');
  const stopBtn = document.getElementById('stopMicBtn');

  if (startBtn) startBtn.addEventListener('click', startMicrophone);
  if (pauseBtn) pauseBtn.addEventListener('click', togglePauseMicrophone);
  if (stopBtn) stopBtn.addEventListener('click', stopMicrophone);

  // Initial status check & standby visualizer
  checkDeviceAvailability();
  drawIdleStandby();
}

async function checkDeviceAvailability() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    updateMicStatus('Disconnected', 'Web Audio API / MediaDevices not supported in this browser.');
    return;
  }

  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const hasAudioInput = devices.some(d => d.kind === 'audioinput');
    if (hasAudioInput) {
      updateMicStatus('Available', 'Microphone hardware detected and ready to connect.');
    } else {
      updateMicStatus('Disconnected', 'No audio input hardware detected.');
    }
  } catch (err) {
    updateMicStatus('Available', 'Ready to request microphone access.');
  }
}

function updateMicStatus(status, message = '') {
  currentMicStatus = status;
  const beacon = document.getElementById('micStatusBeacon');
  const label = document.getElementById('micStatusLabel');
  const details = document.getElementById('micStatusDetails');

  if (!beacon || !label) return;

  // Clear previous state classes
  beacon.className = 'mic-status-beacon';

  switch (status) {
    case 'Available':
      beacon.classList.add('available');
      label.textContent = 'AVAILABLE';
      label.style.color = '#3b82f6';
      break;
    case 'Active':
      beacon.classList.add('active');
      label.textContent = 'ACTIVE (STREAMING)';
      label.style.color = '#10b981';
      break;
    case 'Paused':
      beacon.classList.add('paused');
      label.textContent = 'PAUSED';
      label.style.color = '#f59e0b';
      break;
    case 'Disconnected':
      beacon.classList.add('disconnected');
      label.textContent = 'DISCONNECTED';
      label.style.color = '#64748b';
      break;
    case 'Permission denied':
      beacon.classList.add('denied');
      label.textContent = 'PERMISSION DENIED';
      label.style.color = '#ef4444';
      break;
  }

  if (details && message) {
    details.textContent = message;
  }
}

function getActiveVisThemeColors() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const savedTheme = localStorage.getItem('sonicsentinel_vis_theme') || (isLight ? 'lab' : 'sonar');

  switch (savedTheme) {
    case 'sonar':
      return {
        waveStroke: '#00f5ff',
        barGradStart: '#06b6d4',
        barGradMid: '#3b82f6',
        barGradEnd: '#a855f7'
      };
    case 'emerald':
      return {
        waveStroke: '#10b981',
        barGradStart: '#10b981',
        barGradMid: '#34d399',
        barGradEnd: '#fbbf24'
      };
    case 'cyber':
      return {
        waveStroke: '#38bdf8',
        barGradStart: '#6366f1',
        barGradMid: '#38bdf8',
        barGradEnd: '#ef4444'
      };
    case 'lab':
    default:
      return {
        waveStroke: '#0284c7',
        barGradStart: '#0284c7',
        barGradMid: '#2563eb',
        barGradEnd: '#ef4444'
      };
  }
}

// Redraw on theme change
window.addEventListener('visThemeChanged', () => {
  if (!mediaStream || isPaused) {
    drawIdleStandby();
  }
});

let idleFrameId = null;

function drawIdleStandby() {
  if (mediaStream && !isPaused) return;

  const waveCanvas = document.getElementById('waveformCanvas');
  const specCanvas = document.getElementById('spectrumCanvas');
  const colors = getActiveVisThemeColors();

  // 1. Standby Oscilloscope Baseline
  if (waveCanvas) {
    const ctx = waveCanvas.getContext('2d');
    const w = waveCanvas.width;
    const h = waveCanvas.height;

    ctx.clearRect(0, 0, w, h);
    ctx.lineWidth = 2.4;
    ctx.strokeStyle = colors.waveStroke;
    ctx.beginPath();

    const t = Date.now() * 0.003;
    const points = 120;
    for (let i = 0; i < points; i++) {
      const x = (i / points) * w;
      const y = (h / 2) + Math.sin(t + i * 0.08) * 6 * Math.cos(t * 0.4 + i * 0.04);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // 2. Standby Ambient Bars
  if (specCanvas) {
    const ctx = specCanvas.getContext('2d');
    const w = specCanvas.width;
    const h = specCanvas.height;

    ctx.clearRect(0, 0, w, h);
    const bars = 64;
    const barWidth = (w / bars) - 2;
    const t = Date.now() * 0.002;

    for (let i = 0; i < bars; i++) {
      const val = Math.sin(t + i * 0.18) * 0.5 + 0.5;
      const barHeight = Math.max(4, val * 16 + (i % 4) * 2);
      const x = i * (barWidth + 2);

      const grad = ctx.createLinearGradient(0, h, 0, 0);
      grad.addColorStop(0, colors.barGradStart);
      grad.addColorStop(0.7, colors.barGradMid);
      grad.addColorStop(1, colors.barGradEnd);

      ctx.fillStyle = grad;
      ctx.fillRect(x, h - barHeight, barWidth, barHeight);
    }
  }

  idleFrameId = requestAnimationFrame(drawIdleStandby);
}

async function startMicrophone() {
  try {
    if (idleFrameId) {
      cancelAnimationFrame(idleFrameId);
      idleFrameId = null;
    }

    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false
      }
    });

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    audioContext = new AudioCtx();
    const source = audioContext.createMediaStreamSource(mediaStream);

    analyser = audioContext.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);

    // Capture raw PCM so we can build real WAV windows the backend can decode
    // (no MediaRecorder/webm, no ffmpeg needed).
    liveSampleRate = audioContext.sampleRate;
    pcmChunks = [];
    const bufferSize = 4096;
    scriptNode = audioContext.createScriptProcessor(bufferSize, 1, 1);
    scriptNode.onaudioprocess = (e) => {
      if (isPaused) return;
      pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    source.connect(scriptNode);
    scriptNode.connect(audioContext.destination);

    // Continuous fixed-window monitoring (SRS Step 12): every WINDOW_MS,
    // take the buffered audio, encode to WAV, and classify it.
    if (windowTimer) clearInterval(windowTimer);
    windowTimer = setInterval(processLiveWindow, WINDOW_MS);

    isPaused = false;
    updateMicStatus('Active', 'Listening to acoustic stream in real-time...');

    // UI Button states
    toggleControlButtons(true);

    // Start Visualizer Loop
    drawVisualizer();

  } catch (err) {
    console.error("Microphone error:", err);
    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      updateMicStatus('Permission denied', 'Microphone access was denied by the user. Please allow mic permissions in your browser bar.');
    } else {
      updateMicStatus('Disconnected', `Unable to access microphone: ${err.message}`);
    }
  }
}

function togglePauseMicrophone() {
  if (!audioContext || currentMicStatus === 'Disconnected') return;

  const pauseBtn = document.getElementById('pauseMicBtn');

  if (!isPaused) {
    if (audioContext.state === 'running') {
      audioContext.suspend();
    }
    isPaused = true;
    updateMicStatus('Paused', 'Microphone monitoring paused. Acoustic stream held.');
    if (pauseBtn) pauseBtn.innerHTML = '<i class="fa-solid fa-play"></i> Resume';
  } else {
    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }
    isPaused = false;
    updateMicStatus('Active', 'Resumed live acoustic stream monitoring.');
    if (pauseBtn) pauseBtn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
  }
}

function stopMicrophone() {
  if (windowTimer) { clearInterval(windowTimer); windowTimer = null; }
  if (scriptNode) { try { scriptNode.disconnect(); } catch (e) {} scriptNode = null; }
  pcmChunks = [];
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }

  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  isPaused = false;
  updateMicStatus('Disconnected', 'Microphone disconnected and stream terminated.');
  toggleControlButtons(false);

  // Resume clean standby animation
  drawIdleStandby();
}

function toggleControlButtons(isActive) {
  const startBtn = document.getElementById('startMicBtn');
  const pauseBtn = document.getElementById('pauseMicBtn');
  const stopBtn = document.getElementById('stopMicBtn');

  if (startBtn) startBtn.disabled = isActive;
  if (pauseBtn) {
    pauseBtn.disabled = !isActive;
    pauseBtn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
  }
  if (stopBtn) stopBtn.disabled = !isActive;
}

// Visualizer Canvas Renderer
function drawVisualizer() {
  if (isPaused) {
    animationFrameId = requestAnimationFrame(drawVisualizer);
    return;
  }

  const waveCanvas = document.getElementById('waveformCanvas');
  const specCanvas = document.getElementById('spectrumCanvas');
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';

  const bufferLength = analyser.frequencyBinCount;
  const timeData = new Uint8Array(bufferLength);
  const freqData = new Uint8Array(bufferLength);

  analyser.getByteTimeDomainData(timeData);
  analyser.getByteFrequencyData(freqData);

  const colors = getActiveVisThemeColors();

  // 1. Draw Oscilloscope Waveform
  if (waveCanvas) {
    const ctx = waveCanvas.getContext('2d');
    const width = waveCanvas.width;
    const height = waveCanvas.height;

    ctx.clearRect(0, 0, width, height);
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = colors.waveStroke;
    ctx.beginPath();

    const sliceWidth = width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = timeData[i] / 128.0;
      const y = (v * height) / 2;

      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);

      x += sliceWidth;
    }

    ctx.stroke();
  }

  // 2. Draw Frequency Bars / Spectrogram
  if (specCanvas) {
    const ctx = specCanvas.getContext('2d');
    const width = specCanvas.width;
    const height = specCanvas.height;

    ctx.clearRect(0, 0, width, height);

    const barWidth = (width / 64) - 2;
    let x = 0;

    for (let i = 0; i < 64; i++) {
      const barHeight = (freqData[i * 4] / 255) * height;
      
      const gradient = ctx.createLinearGradient(0, height, 0, 0);
      gradient.addColorStop(0, colors.barGradStart);
      gradient.addColorStop(0.7, colors.barGradMid);
      gradient.addColorStop(1, colors.barGradEnd);

      ctx.fillStyle = gradient;
      ctx.fillRect(x, height - barHeight, barWidth, barHeight);

      x += barWidth + 2;
    }
  }

  // 3. Compute Decibel Level & Peak detection
  let sum = 0;
  for (let i = 0; i < bufferLength; i++) {
    const val = (timeData[i] - 128) / 128;
    sum += val * val;
  }
  const rms = Math.sqrt(sum / bufferLength);
  const db = Math.min(100, Math.max(20, Math.round(20 * Math.log10(rms + 0.0001) + 95)));

  const dbValEl = document.getElementById('liveDbValue');
  const dbBarEl = document.getElementById('liveDbBar');
  if (dbValEl) dbValEl.textContent = `${db} dB`;
  if (dbBarEl) {
    dbBarEl.style.width = `${db}%`;
    dbBarEl.style.backgroundColor = db > 80 ? '#ef4444' : (db > 65 ? '#f59e0b' : '#10b981');
  }

  // Live classification runs continuously via processLiveWindow() on a timer,
  // so no per-frame peak trigger is needed here. Keep the latest dB for display.
  window._liveDb = db;

  animationFrameId = requestAnimationFrame(drawVisualizer);
}

function clearCanvas(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

// Reflect a real per-window classification result on the live dashboard.
function updateLiveResult(data) {
  const db = Math.round(window._liveDb || 0);

  // Update the always-visible live result strip (Python + GTM + agreement).
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('liveResultClass', data.final_class_name || data.final_class);
  set('liveResultPy', `${data.python.confidence}%`);
  set('liveResultGtm', `${data.gtm.confidence}%`);
  set('liveResultAgreement', data.comparison.agreement);
  set('liveResultSeverity', data.severity);
  set('liveResultQuality', data.audio_quality.quality);

  const sevEl = document.getElementById('liveResultSeverity');
  if (sevEl) {
    sevEl.className = 'badge ' + (['Critical', 'High'].includes(data.severity)
      ? 'badge-danger' : (data.severity === 'Medium' ? 'badge-warning' : 'badge-info'));
  }

  // Only raise the critical banner when the backend confirmed an alert
  // (this already accounts for consecutive-window confirmation, Step 15).
  const banner = document.getElementById('liveDetectionBanner');
  if (!banner) return;

  if (data.alert_status === 'Active' || data.confirmed_alert) {
    banner.style.display = 'flex';
    banner.classList.add('flash-alert');
    const nameEl = document.getElementById('detectedEventName');
    const confEl = document.getElementById('detectedEventConfidence');
    const dbEl = document.getElementById('detectedEventDb');
    if (nameEl) nameEl.textContent = data.final_class_name || data.final_class;
    if (confEl) confEl.textContent = `${data.python.confidence}%`;
    if (dbEl) dbEl.textContent = `${db} dB`;
    if (window.acousticSynth && data.severity === 'Critical') {
      window.acousticSynth.playCategorySound('siren');
    }
  }
}
