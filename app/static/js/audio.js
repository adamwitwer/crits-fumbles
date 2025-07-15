// Audio functionality
export function initMuteButton() {
  const muteButton = document.getElementById('mute-button');
  const diceAudio = document.getElementById('dice-sound');
  
  // On load: read saved preference
  const savedMuted = localStorage.getItem('diceMuted') === 'true';
  diceAudio.muted = savedMuted;
  muteButton.textContent = savedMuted ? '🔇' : '🔊';
  muteButton.setAttribute('aria-pressed', savedMuted);
  muteButton.dataset.tooltip = savedMuted ? 'Unmute dice rolling' : 'Mute dice rolling';

  function toggleMute() {
    diceAudio.muted = !diceAudio.muted;
    const nowMuted = diceAudio.muted;

    // Swap icon and aria-pressed as before
    muteButton.textContent = nowMuted ? '🔇' : '🔊';
    muteButton.setAttribute('aria-pressed', nowMuted);

    // Update the tooltip text
    muteButton.dataset.tooltip = nowMuted
      ? 'Unmute dice rolling'
      : 'Mute dice rolling';

    // Persist it
    localStorage.setItem('diceMuted', nowMuted);
  }

  muteButton.addEventListener('click', toggleMute);
}