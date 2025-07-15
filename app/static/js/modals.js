// Modal functionality
import { CONFIG } from './config.js';

// Accessibility tracking
let elementThatTriggeredModal = null;

// Modal Functions with A11y improvements
export function showInfoModal(typeKey, sourceName) {
  const infoModalOverlay = document.getElementById('info-modal-overlay');
  const infoModalTextElement = document.getElementById('info-modal-text');
  const infoModalTitleElement = document.getElementById('info-modal-title');
  const infoModalCloseButton = document.getElementById('info-modal-close-button');
  const mainContent = document.getElementById('main-content');

  const infoText = CONFIG.sourceInfoTexts[typeKey]?.[sourceName];
  if (infoText && infoModalOverlay && infoModalTextElement && infoModalTitleElement) {
    infoModalTextElement.innerHTML = infoText;
    infoModalTitleElement.textContent = `${sourceName}`;
  } else {
    console.warn("No info text found for:", typeKey, sourceName);
    infoModalTextElement.textContent = "Information not available for this selection.";
    infoModalTitleElement.textContent = "Information";
  }

  mainContent.setAttribute('inert', '');
  infoModalOverlay.classList.add('active');

  // Fix: Set focus explicitly
  requestAnimationFrame(() => {
    infoModalCloseButton.focus();
  });
}

export function hideInfoModal() {
  const infoModalOverlay = document.getElementById('info-modal-overlay');
  const mainContent = document.getElementById('main-content');
  
  if (infoModalOverlay) {
    infoModalOverlay.classList.remove('active');
    mainContent.removeAttribute('inert');
    if (elementThatTriggeredModal) {
      elementThatTriggeredModal.focus(); 
      elementThatTriggeredModal = null;
    }
  }
}

// Roll History Functions with A11y improvements
export async function fetchAndDisplayHistory() {
  const showHistoryBtn = document.getElementById('show-history-button');
  const historyOverlay = document.getElementById('history-overlay');
  const historyModal = document.getElementById('history-modal');
  const closeHistoryBtn = document.getElementById('close-history-modal');
  const historyContent = document.getElementById('history-content');
  const mainContent = document.getElementById('main-content');

  try {
    const response = await fetch(window.CF_CONFIG.historyApi);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const logs = await response.json();

    historyContent.innerHTML = ''; 
    if (logs.length === 0) {
      historyContent.innerHTML = '<p>No rolls recorded yet.</p>';
    } else {
      const ul = document.createElement('ul');
      logs.forEach(log => {
        const li = document.createElement('li');
        const time = log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Timestamp unavailable';
        li.innerHTML = `<strong>${time}</strong> ${log.narrative || 'No narrative.'}`;
        ul.appendChild(li);
      });
      historyContent.appendChild(ul);
    }
  } catch (error) {
    console.error('Error fetching roll history:', error);
    historyContent.innerHTML = '<p>Could not load roll history. Please try again later.</p>';
  } finally {
    mainContent.setAttribute('aria-hidden', 'true'); // Hide background
    historyOverlay.classList.add('showing');
    document.body.classList.add('modal-open');
    
    // Use requestAnimationFrame to reliably set focus
    requestAnimationFrame(() => {
      closeHistoryBtn.focus();
    });
  }
}

export function closeHistoryOverlay() {
  const historyOverlay = document.getElementById('history-overlay');
  const mainContent = document.getElementById('main-content');
  
  if (historyOverlay) {
    historyOverlay.classList.remove('showing');
    document.body.classList.remove('modal-open');
    mainContent.removeAttribute('aria-hidden'); // Restore background
    if (elementThatTriggeredModal) {
      elementThatTriggeredModal.focus();
      elementThatTriggeredModal = null;
    }
  }
}

export function setElementThatTriggeredModal(element) {
  elementThatTriggeredModal = element;
}