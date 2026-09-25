/**
 * SonicSentinel - Digital Waveform Animation
 * Animates the signature digital audio wave featured on the landing page radar card
 * (Matching the reference website https://soundeventdetector.eu/ design)
 */

document.addEventListener('DOMContentLoaded', () => {
  initDigitalWaveAnimation();
});

function initDigitalWaveAnimation() {
  const container = document.getElementById('digitalWaveContainer');
  if (!container) return;

  const BAR_COUNT = 38;
  const bars = [];
  container.innerHTML = '';

  // Generate bars
  for (let i = 0; i < BAR_COUNT; i++) {
    const bar = document.createElement('div');
    bar.className = 'digital-wave-bar';
    
    // Highlight central wave region
    const centerDist = Math.abs(i - BAR_COUNT / 2);
    if (centerDist < 6) {
      bar.classList.add('center-peak');
    }
    
    container.appendChild(bar);
    bars.push({
      element: bar,
      baseHeight: Math.max(12, 60 - centerDist * 3.5),
      phase: i * 0.25,
      speed: 0.04 + (i % 3) * 0.015
    });
  }

  let time = 0;
  function animateWave() {
    time += 1;
    bars.forEach((b, idx) => {
      // Harmonic wave formula with fluctuating amplitude
      const centerBias = 1 - (Math.abs(idx - BAR_COUNT / 2) / (BAR_COUNT / 2));
      const waveVal = Math.sin(time * b.speed + b.phase) * Math.cos(time * 0.02 + idx * 0.1);
      const dynamicHeight = Math.max(8, b.baseHeight + waveVal * 28 * centerBias);
      b.element.style.height = `${dynamicHeight}px`;
    });
    requestAnimationFrame(animateWave);
  }

  animateWave();
}
