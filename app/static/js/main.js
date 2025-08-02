// Main application logic - modularized version
import { playDiceSound, createRollHTML, formatKeywords, displayRollingAnimation } from './utils.js';
import { showInfoModal, hideInfoModal, fetchAndDisplayHistory, closeHistoryOverlay, setElementThatTriggeredModal } from './modals.js';
import { toggleFields, updateDamageAndMagicTypes, toggleMagicDropdown, toggleAttackType } from './forms.js';
import { initMuteButton } from './audio.js';
import './webhook.js'; // Import webhook functionality

// --- Global Elements ---
const primaryRollBtn = document.getElementById('primary-roll-button');
const secondaryRollBtn = document.getElementById('secondary-roll-button');
const errorMessageDiv = document.getElementById('error-message');
const primaryResultArea = document.getElementById('primary-result-area');
const secondaryPromptArea = document.getElementById('secondary-prompt-area');
const secondaryResultArea = document.getElementById('secondary-result-area');
const shareButton = document.getElementById('share-discord-button');

// --- Main Roll Handler (AJAX) ---
async function handleRoll(context) {
  playDiceSound();
  errorMessageDiv.style.display = 'none';
  errorMessageDiv.textContent = '';
  primaryRollBtn.disabled = true;
  secondaryRollBtn.disabled = true;
  if (shareButton) {
    shareButton.disabled = true;
    const buttonTextSpan = shareButton.querySelector('.button-text');
    if (buttonTextSpan && buttonTextSpan.textContent === "Shared!") {
      const discordIconHTML = `<img src="${window.CF_CONFIG.discordIcon}" alt="Discord Logo" class="discord-icon">`;
      shareButton.innerHTML = `${discordIconHTML} <span class="button-text">Share Result to Discord</span>`;
    }
  }

  primaryResultArea.innerHTML = '';
  primaryResultArea.style.visibility = 'hidden';
  secondaryResultArea.innerHTML = '';
  secondaryResultArea.style.visibility = 'hidden';
  if (secondaryPromptArea) secondaryPromptArea.style.display = 'none';

  let payload = { rollContext: context };
  let dieTypeForAnim, numDiceForAnim;

  if (context === 'primary') {
    payload.rollType = document.getElementById('roll_type').value;
    const critSource = document.getElementById('crit_source').value;

    if (payload.rollType === 'crit') {
      payload.critSource = critSource;
      let selectedDamageType = document.getElementById('damage_type').value;
      payload.damageType = selectedDamageType; 

      if (critSource === "Sterling Vermin" && selectedDamageType === "magic") {
        payload.magicSubtype = document.getElementById('magic_subtype').value; 
      }
      
      if (critSource === "Questionable Arcana" || critSource === "BCoydog") {
        dieTypeForAnim = 'd100'; 
        numDiceForAnim = 1;      
      } else { // Sterling Vermin crits
        dieTypeForAnim = 'd20';
        numDiceForAnim = 1;
      }
    } else { // fumble
      payload.fumbleType = document.getElementById('fumbleType').value; 
      payload.attackType = document.getElementById('attackType').value; 
      dieTypeForAnim = 'd100'; 
      numDiceForAnim = 1;      
    }
  } else { // context === 'secondary'
    payload.rollType = document.getElementById('secondary-roll-type-hidden').value;
    payload.primaryCritSource = document.getElementById('secondary-crit-source-hidden').value; 
    payload.primaryDamageType = document.getElementById('secondary-damage-type-hidden').value;
    payload.primaryMagicSubtype = document.getElementById('secondary-magic-subtype-hidden').value;
    payload.primaryResultText = document.getElementById('secondary-primary-result-hidden').value;
    payload.primaryRollValue = document.getElementById('secondary-primary-roll-hidden').value;
    dieTypeForAnim = 'd20'; 
    numDiceForAnim = 1;
  }

  displayRollingAnimation(dieTypeForAnim, numDiceForAnim);

  const animationDuration = 1000;
  const overlay = document.getElementById('dice-animation-overlay');

  try {
    const response = await fetch(window.CF_CONFIG.rollAjax, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.errorMessage || `HTTP error! status: ${response.status}`);
    }
    
    setTimeout(() => {
      if (overlay) overlay.style.display = 'none';
      updateUI(data);
    }, animationDuration);

  } catch (error) {
    console.error('Error during fetch or processing:', error);
    if (overlay) overlay.style.display = 'none';
    updateUI({status: 'error', errorMessage: 'Failed to get roll result: ' + error.message});
  } finally {
    primaryRollBtn.disabled = false;
    if (!secondaryPromptArea.style.display || secondaryPromptArea.style.display === 'none' || secondaryPromptArea.style.visibility === 'hidden'){
      secondaryRollBtn.disabled = true;
    } else {
      secondaryRollBtn.disabled = false; 
    }
  }
}

// --- UI Update Function ---
function updateUI(data) {
  let showPrimary = false;
  let showPrompt = false;
  let showSecondary = false;
  let primaryContent = '';
  let secondaryContent = '';
  let elementToScrollTo = null;

  errorMessageDiv.style.display = 'none';
  errorMessageDiv.textContent = '';
  if (shareButton) shareButton.style.display = 'none';

  if (data.status === 'error') {
    errorMessageDiv.textContent = 'Error: ' + (data.errorMessage || 'Unknown error occurred.');
    errorMessageDiv.style.display = 'block';
    elementToScrollTo = errorMessageDiv;
    if (shareButton) shareButton.style.display = 'none';
    primaryRollBtn.disabled = false; 
    secondaryRollBtn.disabled = true; 
  } else {
    const resultClass = data.selectedRollType === 'fumble' ? 'fumble' : 'result';
    let primaryResultExists = false;
    
    const actualNumDiceRolled = data.numDice || 1;
    const actualDieTypeRolled = data.dieType || 'd20';

    if ((data.selectedRollType === 'fumble' || 
         (data.selectedRollType === 'crit' && (data.selectedCritSource === 'Questionable Arcana' || data.selectedCritSource === 'BCoydog'))) &&
        data.description && data.effect && !data.secondaryResultText) {
        
        const formattedDescription = formatKeywords(data.description);
        const formattedEffect = formatKeywords(data.effect);
        const rollValueToShow = data.rollValue;
        const currentResultBoxClass = data.selectedRollType === 'fumble' ? 'fumble' : 'result';
        
        primaryContent = `
            <div class="result-box ${currentResultBoxClass}" data-roll-value="${rollValueToShow}" data-roll-type="${data.selectedRollType}" data-crit-source="${data.selectedCritSource}" data-fumble-source="${data.selectedFumbleType}">
              ${createRollHTML(rollValueToShow, actualNumDiceRolled, actualDieTypeRolled)}
              <div class="description-box">
                 <p>${formattedDescription}</p> 
              </div>
            </div>
            <div class="result-box secondary"> <h2>Effect</h2>
              <p>${formattedEffect}</p>
            </div>`;
        primaryResultExists = true;
    } 
    else if (data.resultText || data.primaryResultForSecondary) {
        const resultTextToShow = data.primaryResultForSecondary || data.resultText || '';
        const formattedResultText = formatKeywords(resultTextToShow);
        const rollValueToShow = data.primaryRollValueForSecondary || data.rollValue;

        let critSourceForPrimaryBoxAtt = data.selectedCritSource;
        let fumbleSourceForPrimaryBoxAtt = data.selectedFumbleType;
        let rollTypeForPrimaryBoxAtt = data.selectedRollType;

        if (data.secondaryResultText) {
            const originalCritSourceFromStorage = document.getElementById('secondary-crit-source-hidden').value;

            if (originalCritSourceFromStorage && originalCritSourceFromStorage !== "null" && originalCritSourceFromStorage !== "undefined" && originalCritSourceFromStorage.trim() !== "") {
                critSourceForPrimaryBoxAtt = originalCritSourceFromStorage;
                fumbleSourceForPrimaryBoxAtt = null;
                rollTypeForPrimaryBoxAtt = 'crit';
            }
        }

        primaryContent = `
            <div class="result-box ${resultClass}"
                 data-roll-value="${rollValueToShow}"
                 data-roll-type="${rollTypeForPrimaryBoxAtt}"
                 data-crit-source="${critSourceForPrimaryBoxAtt !== null && critSourceForPrimaryBoxAtt !== undefined ? critSourceForPrimaryBoxAtt : ''}"
                 data-fumble-source="${fumbleSourceForPrimaryBoxAtt !== null && fumbleSourceForPrimaryBoxAtt !== undefined ? fumbleSourceForPrimaryBoxAtt : ''}">
              ${createRollHTML(rollValueToShow, actualNumDiceRolled, actualDieTypeRolled)}
              <p>${formattedResultText}</p>
              ${data.isSecondaryPrompt && !data.secondaryResultText ? '<p class="scroll-note">👇 Bonus Effect!!! 👇</p>' : ''}
            </div>`;
        primaryResultExists = true;
    }

    if (data.secondaryResultText) { 
        const formattedSecondaryText = formatKeywords(data.secondaryResultText);
        const secondaryRollValue = data.rollValue; 
        secondaryContent = `
            <div class="result-box secondary" data-roll-value="${secondaryRollValue}" data-roll-type="crit-effect">
              <h2>✨ Bonus Effect</h2>
               ${createRollHTML(secondaryRollValue, 1, 'd20')}
               <p>${formattedSecondaryText}</p>
            </div>`;
        showSecondary = true;
    }

    showPrimary = primaryResultExists;
    showPrompt = data.isSecondaryPrompt && !data.secondaryResultText;

    if (showPrompt) {
        document.getElementById('secondary-prompt-text').textContent = data.secondaryPromptText || 'Bonus Effect!';
        document.getElementById('secondary-roll-type-hidden').value = data.secondaryType; 
        
        document.getElementById('secondary-crit-source-hidden').value = data.selectedCritSource;
        document.getElementById('secondary-damage-type-hidden').value = data.original_damageType || document.getElementById('damage_type').value; 
        document.getElementById('secondary-magic-subtype-hidden').value = data.original_magicSubtype || document.getElementById('magic_subtype').value; 
        
        let originalPrimaryText = data.resultText; 
        if (data.selectedRollType === 'crit' && data.description && data.effect) {
            originalPrimaryText = data.description + " Effect: " + data.effect; 
        } else if (!data.resultText && data.description) {
            originalPrimaryText = data.description;
        }
        document.getElementById('secondary-primary-result-hidden').value = originalPrimaryText || "";
        document.getElementById('secondary-primary-roll-hidden').value = data.primaryRollValueForSecondary || data.rollValue || ""; 
        secondaryRollBtn.disabled = false; 
    } else {
        secondaryRollBtn.disabled = true; 
    }

    const isFinalResultShown = showSecondary || (showPrimary && !data.isSecondaryPrompt);
    const hasWebhook = window.webhookManager && window.webhookManager.hasWebhook();
    
    if (isFinalResultShown && data.status !== 'error' && hasWebhook) {
        if (shareButton) {
            shareButton.style.display = 'inline-block';
            shareButton.disabled = false;
            const buttonTextSpan = shareButton.querySelector('.button-text');
            if (buttonTextSpan) { 
              const currentButtonText = buttonTextSpan.textContent;
              if (currentButtonText === "Shared!" || currentButtonText === "Sharing...") {
                  const discordIconHTML = `<img src="${window.CF_CONFIG.discordIcon}" alt="Discord Logo" class="discord-icon">`;
                  shareButton.innerHTML = `${discordIconHTML} <span class="button-text">Share Result to Discord</span>`;
              }
            }
        }
    } else {
        if (shareButton) shareButton.style.display = 'none';
    }
    primaryRollBtn.disabled = false; 
  }

  primaryResultArea.innerHTML = DOMPurify.sanitize(primaryContent);
  primaryResultArea.style.display = showPrimary ? 'block' : 'none';
  primaryResultArea.style.visibility = showPrimary ? 'visible' : 'hidden';

  secondaryPromptArea.style.display = showPrompt ? 'block' : 'none';
  secondaryPromptArea.style.visibility = showPrompt ? 'visible' : 'hidden';

  secondaryResultArea.innerHTML = DOMPurify.sanitize(secondaryContent);
  secondaryResultArea.style.display = showSecondary ? 'block' : 'none';
  secondaryResultArea.style.visibility = showSecondary ? 'visible' : 'hidden';

  if (showSecondary) elementToScrollTo = secondaryResultArea;
  else if (showPrompt) elementToScrollTo = secondaryPromptArea;
  else if (showPrimary && !data.isSecondaryPrompt) elementToScrollTo = primaryResultArea.querySelector('.result-box:not(.secondary)') || primaryResultArea.querySelector('.result-box') || primaryResultArea;
  else if (data.status === 'error') elementToScrollTo = errorMessageDiv;

  if (elementToScrollTo) {
    const style = window.getComputedStyle(elementToScrollTo);
    if (style.display !== 'none' && style.visibility !== 'hidden') {
         elementToScrollTo.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}

// --- Share to Discord Function ---
async function shareResultToDiscord() {
  // Check if webhook is configured
  if (!window.webhookManager || !window.webhookManager.hasWebhook()) {
    alert('Please configure your Discord webhook first by clicking "Configure Discord"');
    return;
  }
  let resultText = '';
  const primaryResultAreaDiv = document.getElementById('primary-result-area');
  const secondaryResultAreaDiv = document.getElementById('secondary-result-area');

  console.log("shareResultToDiscord called. primaryResultAreaDiv:", primaryResultAreaDiv);

  const primaryResultBoxDiv = primaryResultAreaDiv.querySelector('.result-box:not(.secondary)');
  const secondaryBonusEffectBoxDiv = secondaryResultAreaDiv.querySelector('.result-box.secondary');

  console.log("primaryResultBoxDiv:", primaryResultBoxDiv);

  const primaryCritTextP = primaryResultBoxDiv?.querySelector('p:not(.description-box p)');
  const structuredDescP = primaryResultBoxDiv?.querySelector('.description-box p');
  const structuredEffectP = primaryResultAreaDiv.querySelector('.result-box.secondary > p');

  const secondaryBonusEffectP = secondaryBonusEffectBoxDiv?.querySelector('p');

  const primaryRollValue = primaryResultBoxDiv?.dataset.rollValue;
  const secondaryRollValue = secondaryBonusEffectBoxDiv?.dataset.rollValue;

  const critSource = primaryResultBoxDiv?.dataset.critSource;
  const fumbleSource = primaryResultBoxDiv?.dataset.fumbleSource;
  
  let rollType = null;
  if (critSource && critSource !== "null" && critSource !== "undefined") { 
      rollType = 'crit';
  } else if (fumbleSource && fumbleSource !== "null" && fumbleSource !== "undefined") { 
      rollType = 'fumble';
  }
  console.log("Determined rollType:", rollType, "- Crit Source from data:", critSource, "- Fumble Source from data:", fumbleSource);

  let messagePrefix = "\n\u200b\n";

  if (rollType === 'crit') {
      console.log("Share to Discord: Crit path selected.");
      messagePrefix += `💥 **Critical Hit!** 💥\n\n`;
      let critDescription = "";
      let critEffect = "";

      if (critSource === "Questionable Arcana" || critSource === "BCoydog") {
          critDescription = structuredDescP?.textContent.trim() || "N/A";
          critEffect = structuredEffectP?.textContent.trim() || "N/A";
          console.log("Share to Discord - Structured Crit Desc:", critDescription, "Effect:", critEffect);
          resultText = `${messagePrefix}🎲 **Rolled:** ${primaryRollValue ?? '?'}\n📖 **Description:** ${critDescription}\n\n⚠️ **Effect:** ${critEffect}`;
      } else { 
          const primaryText = primaryCritTextP?.textContent.trim() || "N/A";
          console.log("Share to Discord - Sterling Vermin Crit Result:", primaryText);
          resultText = `${messagePrefix}🎲 **Rolled:** ${primaryRollValue ?? '?'}\n⚠️ **Result:** ${primaryText}`;
      }
      if (secondaryBonusEffectP && secondaryBonusEffectP.textContent.trim() && secondaryRollValue) {
          const secondaryText = secondaryBonusEffectP.textContent.trim();
          console.log("Share to Discord - Bonus Effect:", secondaryText);
          resultText += `\n\n🎲 **Bonus Roll:** ${secondaryRollValue}\n✨ **Effect:** ${secondaryText}`;
      }
  } else if (rollType === 'fumble') {
      console.log("Share to Discord: Fumble path selected. Fumble Source:", fumbleSource);
      messagePrefix += `💀 **Fumble!** 💀\n\n`;
      
      const fumbleName = structuredDescP?.textContent.trim() || "N/A";
      const fumbleEffect = structuredEffectP?.textContent.trim() || "N/A";

      console.log("Share to Discord - Fumble Name Element:", structuredDescP);
      console.log("Share to Discord - Fumble Effect Element:", structuredEffectP);
      console.log("Share to Discord - Fumble Name Value:", fumbleName);
      console.log("Share to Discord - Fumble Effect Value:", fumbleEffect);
      
      resultText = `${messagePrefix}🎲 **Rolled:** ${primaryRollValue ?? '?'}\n😩 **Fumble:** ${fumbleName}\n\n⚠️ **Effect:** ${fumbleEffect}`;
  } else {
      console.log("Share to Discord: rollType is null or undefined. Neither crit nor fumble path taken for main content.");
  }
      
  if (!resultText || (resultText.includes('N/A') && !resultText.replace(/N\/A/g, '').replace(messagePrefix, '').trim())) {
      console.log("Share to Discord: Entering fallback logic for resultText construction.");
      const tempPrimaryText = primaryResultAreaDiv.textContent.replace(/(\n|\r|\s{2,})/g, ' ').replace(/Effect/g, '\nEffect').trim();
      const tempSecondaryText = secondaryResultAreaDiv.textContent.replace(/(\n|\r|\s{2,})/g, ' ').trim();
      
      let fallbackPrefix = "\n\u200b\n🎲 **Result:**\n\n";
      if (rollType === 'crit') fallbackPrefix = "\n\u200b\n💥 **Critical Hit!** 💥\n\n";
      else if (rollType === 'fumble') fallbackPrefix = "\n\u200b\n💀 **Fumble!** 💀\n\n";

      if (tempPrimaryText && !tempPrimaryText.toLowerCase().includes("bonus effect!!!")) {
           resultText = `${fallbackPrefix}${tempPrimaryText}`;
           if (tempSecondaryText && tempSecondaryText.toLowerCase().includes("bonus effect")) { 
               resultText += `\n✨ ${tempSecondaryText.replace(/Bonus Effect/i, '').trim()}`;
           } else if (tempSecondaryText) {
               resultText += `\nBonus: ${tempSecondaryText}`;
           }
      } else {
          console.warn("shareResultToDiscord: No valid result text found to share even after fallback.");
          alert('Could not find a complete result to share!');
          const originalButtonHTML_fallback = shareButton.innerHTML; 
          const discordIconHTML_fallback = shareButton.querySelector('.discord-icon')?.outerHTML || '';
           if(shareButton.querySelector('.button-text')?.textContent === "Sharing..."){
              shareButton.innerHTML = originalButtonHTML_fallback;
           }
          shareButton.disabled = false;
          return;
      }
  }
  
  console.log("Final resultText for Discord:", resultText);
  
  const discordIconHTML = shareButton.querySelector('.discord-icon')?.outerHTML || '';
  const originalButtonHTML = shareButton.innerHTML; 

  shareButton.disabled = true;
  shareButton.innerHTML = `${discordIconHTML} <span class="button-text">Sharing...</span>`;

  try {
      // Get webhook URL from webhook manager and send via server
      const webhookUrl = window.webhookManager.getCurrentWebhookURL();
      
      const response = await fetch(window.CF_CONFIG.shareDiscord, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify({ 
              message: resultText,
              webhookUrl: webhookUrl 
          })
      });
      
      const responseData = await response.json();
      if (response.ok && responseData.status === 'success') {
          shareButton.innerHTML = `${discordIconHTML} <span class="button-text">Shared!</span>`;
          setTimeout(() => {
              if (shareButton.style.display !== 'none') { 
                  shareButton.innerHTML = originalButtonHTML; 
                  shareButton.disabled = false;
              }
          }, 2000);
      } else {
          alert(`Failed to share result: ${responseData?.error || response.statusText}`);
          shareButton.innerHTML = originalButtonHTML;
          shareButton.disabled = false;
      }
  } catch (error) {
       alert('Error contacting server to share result.');
       console.error("Share to Discord error:", error);
       shareButton.innerHTML = originalButtonHTML;
       shareButton.disabled = false;
  }
}

// --- Event Setup and Initialization ---
function setupEventListeners() {
  // Get references to elements
  const rollTypeSelect = document.getElementById('roll_type');
  const critSourceSelect = document.getElementById('crit_source');
  const damageTypeSelect = document.getElementById('damage_type');
  const fumbleTypeSelect = document.getElementById('fumbleType');
  const critSourceInfoIcon = document.getElementById('crit_source_info_icon');
  const fumbleTypeInfoIcon = document.getElementById('fumble_type_info_icon');
  const showHistoryBtn = document.getElementById('show-history-button');
  const infoModalCloseButton = document.getElementById('info-modal-close-button');
  const infoModalOverlay = document.getElementById('info-modal-overlay');
  const closeHistoryBtn = document.getElementById('close-history-modal');
  const historyOverlay = document.getElementById('history-overlay');

  // Attach event listeners for forms
  if (rollTypeSelect) rollTypeSelect.addEventListener('change', toggleFields);
  if (critSourceSelect) critSourceSelect.addEventListener('change', updateDamageAndMagicTypes);
  if (damageTypeSelect) damageTypeSelect.addEventListener('change', toggleMagicDropdown);
  if (fumbleTypeSelect) fumbleTypeSelect.addEventListener('change', toggleAttackType);
  if (primaryRollBtn) primaryRollBtn.addEventListener('click', () => handleRoll('primary'));
  if (secondaryRollBtn) secondaryRollBtn.addEventListener('click', () => handleRoll('secondary'));
  if (shareButton) shareButton.addEventListener('click', shareResultToDiscord);

  // Event Listeners for opening Info Modal
  if (critSourceInfoIcon) {
      critSourceInfoIcon.addEventListener('click', () => {
          setElementThatTriggeredModal(document.activeElement);
          const selectedCritSource = document.getElementById('crit_source').value;
          showInfoModal('critSources', selectedCritSource);
      });
  }
  if (fumbleTypeInfoIcon) {
      fumbleTypeInfoIcon.addEventListener('click', () => {
          setElementThatTriggeredModal(document.activeElement);
          const selectedFumbleSource = document.getElementById('fumbleType').value;
          showInfoModal('fumbleSources', selectedFumbleSource);
      });
  }

  // Event listeners for closing Info Modal
  if (infoModalCloseButton) infoModalCloseButton.addEventListener('click', hideInfoModal);
  if (infoModalOverlay) {
      infoModalOverlay.addEventListener('click', (event) => {
          if (event.target === infoModalOverlay) hideInfoModal();
      });
  }
  
  // Event Listeners for opening History Modal
  if (showHistoryBtn) {
    showHistoryBtn.addEventListener('click', () => {
      setElementThatTriggeredModal(document.activeElement);
      fetchAndDisplayHistory();
    });
  }

  // Event Listeners for closing History Modal
  if (closeHistoryBtn) closeHistoryBtn.addEventListener('click', closeHistoryOverlay);
  if (historyOverlay) {
      historyOverlay.addEventListener('click', (event) => {
          if (event.target === historyOverlay) closeHistoryOverlay();
      });
  }
  
  // Global keyboard listener for modal control (Escape key and Focus Trapping)
  document.addEventListener('keydown', (event) => {
      const infoModalOverlay = document.getElementById('info-modal-overlay');
      const historyOverlay = document.getElementById('history-overlay');
      const webhookModalOverlay = document.getElementById('webhook-modal-overlay');
      const infoModal = document.getElementById('info-modal');
      const historyModal = document.getElementById('history-modal');
      const webhookModal = document.getElementById('webhook-modal');

      const isInfoModalActive = infoModalOverlay.classList.contains('active');
      const isHistoryModalActive = historyOverlay.classList.contains('showing');
      const isWebhookModalActive = webhookModalOverlay.classList.contains('active');

      if (event.key === 'Escape') {
          if (isInfoModalActive) hideInfoModal();
          if (isHistoryModalActive) closeHistoryOverlay();
          if (isWebhookModalActive && window.webhookManager) window.webhookManager.closeWebhookModal();
      }

      if (event.key === 'Tab') {
          let activeModalContent = null;
          if (isInfoModalActive) activeModalContent = infoModal;
          else if (isHistoryModalActive) activeModalContent = historyModal;
          else if (isWebhookModalActive) activeModalContent = webhookModal;

          if (activeModalContent) {
              const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
              const allFocusableElements = Array.from(activeModalContent.querySelectorAll(focusableSelector));
              
              // Filter out elements that are hidden (display: none or visibility: hidden)
              const focusableElements = allFocusableElements.filter(element => {
                  const style = window.getComputedStyle(element);
                  return style.display !== 'none' && style.visibility !== 'hidden';
              });
              
              if (focusableElements.length === 0) return;

              const firstElement = focusableElements[0];
              const lastElement = focusableElements[focusableElements.length - 1];

              if (event.shiftKey) { // Shift + Tab
                  if (document.activeElement === firstElement) {
                      lastElement.focus();
                      event.preventDefault();
                  }
              } else { // Tab
                  if (document.activeElement === lastElement) {
                      firstElement.focus();
                      event.preventDefault();
                  }
              }
          }
      }
  });
}

// --- Initial Setup on Load ---
window.onload = function() {
  setupEventListeners();
  initMuteButton();
  toggleFields(); // Initial setup
};