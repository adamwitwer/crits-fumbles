// Utility functions

export function playDiceSound() {
  const diceAudio = document.getElementById('dice-sound');
  if (diceAudio) {
    diceAudio.currentTime = 0;
    diceAudio.play().catch(error => console.error("Audio play failed:", error));
  }
}

export function createRollHTML(rollValue, numDice, dieType) {
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

const CONDITION_URLS = {
  'Blinded':       'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#BlindedCondition',
  'Deafened':      'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#DeafenedCondition',
  'Frightened':    'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#FrightenedCondition',
  'Grappled':      'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#GrappledCondition',
  'Incapacitated': 'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#IncapacitatedCondition',
  'Paralyzed':     'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#ParalyzedCondition',
  'Petrified':     'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#PetrifiedCondition',
  'Poisoned':      'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#PoisonedCondition',
  'Prone':         'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#ProneCondition',
  'Restrained':    'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#RestrainedCondition',
  'Stunned':       'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#StunnedCondition',
  'Unconscious':   'https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#UnconsciousCondition',
};

const CONDITION_PATTERN = new RegExp(
  '\\b(' + Object.keys(CONDITION_URLS).join('|') + ')\\b', 'g'
);

export function formatKeywords(text) {
  if (!text) return "";
  const keywordClass = "keyword-prefix";
  let formattedText = text.replaceAll("Melee:", `<span class="${keywordClass}">Melee:</span>`);
  formattedText = formattedText.replaceAll("Ranged:", `<br><br><span class="${keywordClass}">Ranged:</span>`);
  formattedText = formattedText.replace(CONDITION_PATTERN, (match) => {
    const url = CONDITION_URLS[match];
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="condition-link">${match}</a>`;
  });
  return formattedText;
}

export function displayRollingAnimation(dieType, numDice) {
  const overlay = document.getElementById('dice-animation-overlay');
  const animContainer = overlay.querySelector('.rolling-animation-container');
  animContainer.innerHTML = '';

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