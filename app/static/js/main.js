  // --- Global Elements ---
  const diceAudio = document.getElementById('dice-sound');
  const primaryRollBtn = document.getElementById('primary-roll-button');
  const secondaryRollBtn = document.getElementById('secondary-roll-button');
  const errorMessageDiv = document.getElementById('error-message');
  const primaryResultArea = document.getElementById('primary-result-area');
  const secondaryPromptArea = document.getElementById('secondary-prompt-area');
  const secondaryResultArea = document.getElementById('secondary-result-area');
  const shareButton = document.getElementById('share-discord-button');
  const mainContent = document.getElementById('main-content'); // Main content wrapper

  // --- Modal Elements ---
  const infoModalOverlay = document.getElementById('info-modal-overlay');
  const infoModal = document.getElementById('info-modal');
  const infoModalTextElement = document.getElementById('info-modal-text');
  const infoModalTitleElement = document.getElementById('info-modal-title');
  const infoModalCloseButton = document.getElementById('info-modal-close-button');
  const critSourceInfoIcon = document.getElementById('crit_source_info_icon');
  const fumbleTypeInfoIcon = document.getElementById('fumble_type_info_icon');
  
  // --- History Modal Elements ---
  const showHistoryBtn = document.getElementById('show-history-button');
  const historyOverlay = document.getElementById('history-overlay');
  const historyModal = document.getElementById('history-modal');
  const closeHistoryBtn = document.getElementById('close-history-modal');
  const historyContent = document.getElementById('history-content');

  // --- Accessibility Enhancements ---
  let elementThatTriggeredModal = null;

  // --- Data for Dynamic Dropdowns & Info Modals ---
  const critSourceDamageTypes = {
      "Sterling Vermin": {
          options: ["bludgeoning", "piercing", "slashing", "magic"],
          magicSubtypes: {
              "magic:acid": "Acid", "magic:cold": "Cold", "magic:fire": "Fire",
              "magic:force": "Force", "magic:lightning": "Lightning", "magic:necrotic": "Necrotic",
              "magic:poison": "Poison", "magic:psychic": "Psychic", "magic:radiant": "Radiant",
              "magic:thunder": "Thunder"
          }
      },
      "Questionable Arcana": { options: ["weapon", "spell"], magicSubtypes: {} },
      "BCoydog": { options: ["melee", "ranged", "magic"], magicSubtypes: {} }
  };

  const sourceInfoTexts = {
      critSources: {
          "Sterling Vermin": "<a target='_blank' rel='noopener noreferrer' href='https://sterlingvermin.wordpress.com/2016/09/27/critical-hits-revisited/'>Critical Hits Revisited</a> offers d20 results with comprehensive damage types, including magic subtypes and insanities.",
          "Questionable Arcana": "These d100 critical hit tables from <a target='_blank' rel='noopener noreferrer' href='https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/'>Questionable Arcana</a> provide narrative and situational effects, often with a unique twist. They are broadly categorized (e.g., Weapon, Spell) and complemented by the QA fumble tables.",
          "BCoydog": "Reddit user u/BCoydog shared these critical hit tables in <a target='_blank' rel='noopener noreferrer' href='https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/'>the DnD subreddit</a>. Expect wild (but fair) outcomes for melee, ranged, and magic attacks, often with detailed descriptions and mechanical impacts. Accompanied by a fumble <span class='nowrap'>table</span>."
      },
      fumbleSources: {
          "Questionable Arcana": "The <a target='_blank' rel='noopener noreferrer' href='https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/'>Questionable Arcana</a> d100 fumble tables focus on the story consequences of fumbled weapon or spell attacks.",
          "BCoydog": "Reddit user u/BCoydog’s <a target='_blank' rel='noopener noreferrer' href='https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/'>d100 fumble tables</a> feature humorous or challenging results for fumbled melee, ranged, or magic actions."
      }
  };

  // --- Modal Functions (with new A11y improvements) ---
  function showInfoModal(typeKey, sourceName) {
    const infoText = sourceInfoTexts[typeKey]?.[sourceName];
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

    // 🔧 Fix: Set focus explicitly
    requestAnimationFrame(() => {
        infoModalCloseButton.focus();
    });
}

  function hideInfoModal() {
      if (infoModalOverlay) {
          infoModalOverlay.classList.remove('active');
          mainContent.removeAttribute('inert');
          if (elementThatTriggeredModal) {
              elementThatTriggeredModal.focus(); 
              elementThatTriggeredModal = null;
          }
       }
  }

  // --- Roll History Functions (with new A11y improvements) ---
  async function fetchAndDisplayHistory() {
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

  function closeHistoryOverlay() {
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

  // --- UI Toggle Functions ---
  function toggleAttackType() {
    const fumbleTypeSelect = document.getElementById('fumbleType');
    const selectedFumbleType = fumbleTypeSelect.value;
    const attackTypeContainer = document.getElementById('attack-type-container');
    const attackTypeSelect = document.getElementById('attackType');
    const rollType = document.getElementById('roll_type').value;
    const currentAttackTypeValue = attackTypeSelect.value;
    attackTypeSelect.innerHTML = ''; 
    if (rollType === 'fumble') {
        let newOptions = [];
        if (selectedFumbleType === "Questionable Arcana") {
            newOptions = [{ value: "Weapon", text: "Weapon" }, { value: "Magic", text: "Magic" }];
            attackTypeContainer.style.display = 'block';
        } else if (selectedFumbleType === "BCoydog") {
            newOptions = [{ value: "melee", text: "Melee" }, { value: "ranged", text: "Ranged" }, { value: "magic", text: "Magic" }];
            attackTypeContainer.style.display = 'block';
        } else {
            attackTypeContainer.style.display = 'none';
        }
        let valueToSet = null;
        newOptions.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value;
            option.textContent = opt.text;
            attackTypeSelect.appendChild(option);
            if (opt.value === currentAttackTypeValue) {
                valueToSet = currentAttackTypeValue;
            }
        });
        if (valueToSet) {
            attackTypeSelect.value = valueToSet;
        } else if (attackTypeSelect.options.length > 0) {
            attackTypeSelect.value = attackTypeSelect.options[0].value;
        }
    } else {
        attackTypeContainer.style.display = 'none';
    }
  }

  function toggleFields() {
    const rollType = document.getElementById('roll_type').value;
    const critFields = document.getElementById('crit-fields');
    const fumbleTypeContainer = document.getElementById('fumble-type-container');
    const attackTypeContainer = document.getElementById('attack-type-container');
    const critSourceContainer = document.getElementById('crit-source-container');
    const currentCritSourceInfoIcon = document.getElementById('crit_source_info_icon');
    const currentFumbleTypeInfoIcon = document.getElementById('fumble_type_info_icon');
    if (rollType === 'fumble') {
      critFields.style.display = 'none';
      critSourceContainer.style.display = 'none';
      if(currentCritSourceInfoIcon) currentCritSourceInfoIcon.style.display = 'none';
      fumbleTypeContainer.style.display = 'block';
      if(currentFumbleTypeInfoIcon) currentFumbleTypeInfoIcon.style.display = 'inline-block'; 
      toggleAttackType();
    } else { // crit
      critFields.style.display = 'block';
      critSourceContainer.style.display = 'block';
      if(currentCritSourceInfoIcon) currentCritSourceInfoIcon.style.display = 'inline-block'; 
      fumbleTypeContainer.style.display = 'none';
      if(currentFumbleTypeInfoIcon) currentFumbleTypeInfoIcon.style.display = 'none';
      attackTypeContainer.style.display = 'none';
      updateDamageAndMagicTypes(); 
    }
  }
  
  // --- Helper Functions ---
  function playDiceSound() {
    if (diceAudio) {
      diceAudio.currentTime = 0;
      diceAudio.play().catch(error => console.error("Audio play failed:", error));
    }
  }

  function createRollHTML(rollValue, numDice, dieType) {
  // Decide which image to show:
  // - For a single d100 roll we want two d10 images.
  // - Otherwise use the dieType passed in.
  let imgSrc;
  if (dieType === 'd100' && numDice === 1) {
    imgSrc = window.CF_CONFIG.d10Img;
  } else {
    imgSrc = `${window.CF_CONFIG.imgBase}${dieType}.webp`;
  }

  // Build the HTML:
  let html = '<div class="roll-result">';
  html += `<img src="${imgSrc}" alt="${dieType}" class="inline-die">`;
  html += `<span class="roll-value">${rollValue ?? '?'}</span>`;

  // If it's a d100, show the second d10:
  if (dieType === 'd100' && numDice === 1) {
    html += `<img src="${window.CF_CONFIG.d10Img}" alt="d10" class="inline-die">`;
  }

  html += '</div>';
  return html;
 }

  function formatKeywords(text) {
      if (!text) return "";
      const keywordClass = "keyword-prefix";
      let formattedText = text.replaceAll("Melee:", `<span class="${keywordClass}">Melee:</span>`);
      formattedText = formattedText.replaceAll("Ranged:", `<br><br><span class="${keywordClass}">Ranged:</span>`);
      return formattedText;
  }

  function displayRollingAnimation(dieType, numDice) {
      
      const overlay = document.getElementById('dice-animation-overlay');
      // The container is now guaranteed to exist; helps with cold start.
      const animContainer = overlay.querySelector('.rolling-animation-container');
      
      // Clear contents before adding new dice.
      animContainer.innerHTML = ''; 
      
      if (!animContainer) {
          animContainer = document.createElement('div');
          animContainer.classList.add('rolling-animation-container');
          overlay.appendChild(animContainer);
      } else {
          animContainer.innerHTML = '';
      }
      let actualNumDiceForAnim = numDice;
      let actualDieTypeForAnim = dieType;
      if (dieType === 'd100' && numDice === 1) { 
          actualDieTypeForAnim = 'd10'; 
          actualNumDiceForAnim = 2;     
      }
      const dieImageSrc = `${window.CF_CONFIG.imgBase}${actualDieTypeForAnim}.webp`;
      for (let i = 0; i < actualNumDiceForAnim; i++) {
          const img = document.createElement('img');
          img.src = dieImageSrc;
          img.alt = actualDieTypeForAnim;
          img.classList.add('inline-die', 'is-rolling');
          animContainer.appendChild(img);
      }
      overlay.style.display = 'flex';
  }

   function updateDamageAndMagicTypes() {
       const critSource = document.getElementById('crit_source').value;
       const damageTypeSelect = document.getElementById('damage_type');
       const magicSubtypeContainer = document.getElementById('magic-subtype');
       const magicSubtypeSelect = document.getElementById('magic_subtype');
       damageTypeSelect.innerHTML = '';
       magicSubtypeSelect.innerHTML = '';
       magicSubtypeContainer.style.display = 'none';
       const sourceData = critSourceDamageTypes[critSource];
       if (sourceData) {
           sourceData.options.forEach(type => {
               const option = document.createElement('option');
               option.value = type; 
               option.textContent = type.charAt(0).toUpperCase() + type.slice(1); 
               damageTypeSelect.appendChild(option);
           });
           toggleMagicDropdown(); 
       } else {
           const option = document.createElement('option');
           option.value = "";
           option.textContent = "Select Crit Source";
           damageTypeSelect.appendChild(option);
       }
   }

  function toggleMagicDropdown() {
    const critSource = document.getElementById('crit_source').value;
    const damageType = document.getElementById('damage_type').value; 
    const magicSubtypeContainer = document.getElementById('magic-subtype');
    const magicSubtypeSelect = document.getElementById('magic_subtype');
    magicSubtypeContainer.style.display = 'none';
    magicSubtypeSelect.innerHTML = '';
    if (critSource === "Sterling Vermin" && damageType === "magic") {
        const sterlingVerminMagicSubtypes = critSourceDamageTypes["Sterling Vermin"].magicSubtypes;
        if (sterlingVerminMagicSubtypes) {
            for (const key in sterlingVerminMagicSubtypes) { 
                const option = document.createElement('option');
                option.value = key; 
                option.textContent = sterlingVerminMagicSubtypes[key]; 
                magicSubtypeSelect.appendChild(option);
            }
            magicSubtypeContainer.style.display = 'block';
        }
    }
  }

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
          payload.primaryDamageType = document.getElementById('secondary-damage-type-hidden').value; // Uses data.original_damageType
          payload.primaryMagicSubtype = document.getElementById('secondary-magic-subtype-hidden').value; // Uses data.original_magicSubtype
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
              // const rollTypeForDataAttr = data.selectedRollType; // Original line for data-roll-type

              let critSourceForPrimaryBoxAtt = data.selectedCritSource; // Default to current response's crit source
              let fumbleSourceForPrimaryBoxAtt = data.selectedFumbleType; // Default to current response's fumble type
              let rollTypeForPrimaryBoxAtt = data.selectedRollType; // Default to current response's roll type

              // If this UI update is for displaying the result of a secondary roll,
              // the primary box's data attributes should reflect the original roll's context.
              if (data.secondaryResultText) {
                  const originalCritSourceFromStorage = document.getElementById('secondary-crit-source-hidden').value;
                  // const originalFumbleSourceFromStorage = document.getElementById('secondary-fumble-source-hidden')?.value; // Assuming a similar field if fumbles had bonuses

                  // If a valid original crit source was stored, use it.
                  if (originalCritSourceFromStorage && originalCritSourceFromStorage !== "null" && originalCritSourceFromStorage !== "undefined" && originalCritSourceFromStorage.trim() !== "") {
                      critSourceForPrimaryBoxAtt = originalCritSourceFromStorage;
                      fumbleSourceForPrimaryBoxAtt = null; // Clear fumble if original was a crit
                      // For consistency, the data-roll-type of the primary box should also reflect it was a 'crit'.
                      // The original roll_type that initiated the crit sequence is what's desired here.
                      // This might need to be stored similarly, or inferred.
                      // For now, setting to 'crit' if originalCritSource is present.
                      rollTypeForPrimaryBoxAtt = 'crit';
                  }
                  // Add similar logic for fumble if fumbles can have secondary rolls affecting the primary box display.
                  // else if (originalFumbleSourceFromStorage && originalFumbleSourceFromStorage !== "null" && ...) {
                  // fumbleSourceForPrimaryBoxAtt = originalFumbleSourceFromStorage;
                  // critSourceForPrimaryBoxAtt = null;
                  // rollTypeForPrimaryBoxAtt = 'fumble';
                  // }
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
          if (isFinalResultShown && data.status !== 'error') {
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
        const response = await fetch(window.CF_CONFIG.shareDiscord, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ message: resultText })
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
  
  // --- Mute Button ---
  const muteButton = document.getElementById('mute-button');
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

  // --- Roll History Functions ---
  async function fetchAndDisplayHistory() {
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

        historyOverlay.classList.add('showing');
        document.body.classList.add('modal-open');
        closeHistoryBtn.focus(); // Set focus on the close button
        
    } catch (error) {
        console.error('Error fetching roll history:', error);
        historyContent.innerHTML = '<p>Could not load roll history. Please try again later.</p>';
        historyOverlay.classList.add('showing');
        document.body.classList.add('modal-open');
        closeHistoryBtn.focus(); // Set focus on the close button
    }
 }

 function closeHistoryOverlay() {
    if (historyOverlay) {
        historyOverlay.classList.remove('showing');
        document.body.classList.remove('modal-open');
        if (elementThatTriggeredModal) {
            elementThatTriggeredModal.focus(); // Return focus
            elementThatTriggeredModal = null;
        }
    }
 }

  // --- Initial Setup on Load ---
  window.onload = function() {
    // --- Event Listeners for Forms and Inputs ---

    // Get references to elements that previously had inline handlers
    const rollTypeSelect = document.getElementById('roll_type');
    const critSourceSelect = document.getElementById('crit_source');
    const damageTypeSelect = document.getElementById('damage_type');
    const fumbleTypeSelect = document.getElementById('fumbleType');
    const primaryRollBtn = document.getElementById('primary-roll-button');
    const secondaryRollBtn = document.getElementById('secondary-roll-button');

    // Attach event listeners
    if (rollTypeSelect) {
        rollTypeSelect.addEventListener('change', toggleFields);
    }
    if (critSourceSelect) {
        critSourceSelect.addEventListener('change', updateDamageAndMagicTypes);
    }
    if (damageTypeSelect) {
        damageTypeSelect.addEventListener('change', toggleMagicDropdown);
    }
    if (fumbleTypeSelect) {
        fumbleTypeSelect.addEventListener('change', toggleAttackType);
    }
    if (primaryRollBtn) {
        primaryRollBtn.addEventListener('click', () => handleRoll('primary'));
    }
    if (secondaryRollBtn) {
        secondaryRollBtn.addEventListener('click', () => handleRoll('secondary'));
    }
      if (shareButton) {
        shareButton.addEventListener('click', shareResultToDiscord);
    }

    // Event Listeners for opening Info Modal
    if (critSourceInfoIcon) {
        critSourceInfoIcon.addEventListener('click', () => {
            elementThatTriggeredModal = document.activeElement;
            const selectedCritSource = document.getElementById('crit_source').value;
            showInfoModal('critSources', selectedCritSource);
        });
    }
    if (fumbleTypeInfoIcon) {
        fumbleTypeInfoIcon.addEventListener('click', () => {
            elementThatTriggeredModal = document.activeElement;
            const selectedFumbleSource = document.getElementById('fumbleType').value;
            showInfoModal('fumbleSources', selectedFumbleSource);
        });
    }

    // Event listeners for closing Info Modal
    if (infoModalCloseButton) {
        infoModalCloseButton.addEventListener('click', hideInfoModal);
    }
    if (infoModalOverlay) {
        infoModalOverlay.addEventListener('click', (event) => {
            if (event.target === infoModalOverlay) {
                hideInfoModal();
            }
        });
    }
    
    // Event Listeners for opening History Modal
    if (showHistoryBtn) {
      showHistoryBtn.addEventListener('click', () => {
        elementThatTriggeredModal = document.activeElement;
        fetchAndDisplayHistory();
      });
    }

    // Event Listeners for closing History Modal
    if (closeHistoryBtn) {
        closeHistoryBtn.addEventListener('click', closeHistoryOverlay);
    }
    if (historyOverlay) {
        historyOverlay.addEventListener('click', (event) => {
            if (event.target === historyOverlay) {
                closeHistoryOverlay();
            }
        });
    }
    
    // Global keyboard listener for modal control (Escape key and Focus Trapping)
    document.addEventListener('keydown', (event) => {
        const isInfoModalActive = infoModalOverlay.classList.contains('active');
        const isHistoryModalActive = historyOverlay.classList.contains('showing');

        if (event.key === 'Escape') {
            if (isInfoModalActive) hideInfoModal();
            if (isHistoryModalActive) closeHistoryOverlay();
        }

        if (event.key === 'Tab') {
            let activeModalContent = null;
            if (isInfoModalActive) activeModalContent = infoModal;
            else if (isHistoryModalActive) activeModalContent = historyModal;

            if (activeModalContent) {
                const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
                const focusableElements = Array.from(activeModalContent.querySelectorAll(focusableSelector));
                
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
    
    toggleFields(); // Initial setup
};