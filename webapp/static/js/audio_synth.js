/**
 * SonicSentinel - Acoustic Audio Synthesizer
 * Synthesizes realistic acoustic sound previews for all 10 mandatory sound categories
 * using browser Web Audio API (Zero external audio assets required).
 */

class AcousticSynthesizer {
  constructor() {
    this.ctx = null;
    this.currentPlayingBtn = null;
  }

  initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  playCategorySound(categoryKey, btnElement = null) {
    this.initContext();

    if (this.currentPlayingBtn) {
      this.currentPlayingBtn.classList.remove('playing');
    }

    if (btnElement) {
      this.currentPlayingBtn = btnElement;
      btnElement.classList.add('playing');
    }

    const t = this.ctx.currentTime;

    switch (categoryKey) {
      case 'gunshot':
        this.synthGunshot(t);
        break;
      case 'panic_scream':
      case 'scream':
        this.synthScream(t);
        break;
      case 'glass_breaking':
      case 'glass':
        this.synthGlassBreak(t);
        break;
      case 'alarm_siren':
      case 'siren':
        this.synthSiren(t);
        break;
      case 'vehicle_horn':
      case 'horn':
        this.synthHorn(t);
        break;
      case 'animal_sound':
      case 'animal':
        this.synthAnimal(t);
        break;
      case 'aggression_conflict':
      case 'aggression':
        this.synthAggression(t);
        break;
      case 'machinery_fault':
      case 'machinery':
        this.synthMachinery(t);
        break;
      case 'person_help':
      case 'help':
        this.synthHelpCall(t);
        break;
      case 'background_noise':
      case 'noise':
      default:
        this.synthNoise(t);
        break;
    }

    // Reset button icon after play
    setTimeout(() => {
      if (this.currentPlayingBtn) {
        this.currentPlayingBtn.classList.remove('playing');
        this.currentPlayingBtn = null;
      }
    }, 1500);
  }

  // 1. Gunshot: Sudden explosive crack + rapid decaying sub-bass thud
  synthGunshot(t) {
    const bufferSize = this.ctx.sampleRate * 0.4;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(1200, t);
    filter.frequency.exponentialRampToValueAtTime(100, t + 0.35);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(1.0, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.35);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);
    noise.start(t);
  }

  // 2. Panic Scream: High-pitched frequency sweep with jitter
  synthScream(t) {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sawtooth';

    osc.frequency.setValueAtTime(650, t);
    osc.frequency.linearRampToValueAtTime(1150, t + 0.4);
    osc.frequency.exponentialRampToValueAtTime(700, t + 1.2);

    gain.gain.setValueAtTime(0.01, t);
    gain.gain.linearRampToValueAtTime(0.35, t + 0.15);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 1.3);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 1.3);
  }

  // 3. Glass Breaking: High resonant chatter bursts
  synthGlassBreak(t) {
    const bufferSize = this.ctx.sampleRate * 0.6;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (this.ctx.sampleRate * 0.1));
    }
    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.setValueAtTime(3500, t);

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.8, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.6);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);
    noise.start(t);
  }

  // 4. Siren: Modulating two-tone emergency alarm
  synthSiren(t) {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';

    // Wailing siren modulation
    osc.frequency.setValueAtTime(600, t);
    osc.frequency.linearRampToValueAtTime(950, t + 0.4);
    osc.frequency.linearRampToValueAtTime(600, t + 0.8);
    osc.frequency.linearRampToValueAtTime(950, t + 1.2);
    osc.frequency.linearRampToValueAtTime(600, t + 1.5);

    gain.gain.setValueAtTime(0.25, t);
    gain.gain.linearRampToValueAtTime(0.25, t + 1.3);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 1.5);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 1.5);
  }

  // 5. Vehicle Horn: Dual chord blare
  synthHorn(t) {
    [340, 420].forEach(freq => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(freq, t);

      gain.gain.setValueAtTime(0.18, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 1.0);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 1.0);
    });
  }

  // 6. Animal Sound: Barking pulses
  synthAnimal(t) {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(320, t);
    osc.frequency.linearRampToValueAtTime(180, t + 0.25);

    gain.gain.setValueAtTime(0.4, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.35);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 0.4);
  }

  // 7. Aggression Conflict: Harsh shouting distortion
  synthAggression(t) {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(220, t);
    osc.frequency.linearRampToValueAtTime(360, t + 0.4);
    osc.frequency.exponentialRampToValueAtTime(190, t + 1.1);

    gain.gain.setValueAtTime(0.3, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 1.2);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 1.2);
  }

  // 8. Machinery Fault: Low rumble and mechanical grind
  synthMachinery(t) {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'square';
    osc.frequency.setValueAtTime(85, t);
    osc.frequency.linearRampToValueAtTime(110, t + 0.6);

    gain.gain.setValueAtTime(0.2, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 1.4);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 1.4);
  }

  // 9. Help Call: Emergency tone pair
  synthHelpCall(t) {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(520, t);
    osc.frequency.setValueAtTime(780, t + 0.3);
    osc.frequency.setValueAtTime(520, t + 0.6);

    gain.gain.setValueAtTime(0.25, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 1.2);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + 1.2);
  }

  // 10. Background Noise: Filtered pink noise
  synthNoise(t) {
    const bufferSize = this.ctx.sampleRate * 1.5;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * 0.15;
    }
    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;
    noise.connect(this.ctx.destination);
    noise.start(t);
  }
}

window.acousticSynth = new AcousticSynthesizer();
