// Form handling and UI toggle functions
import { CONFIG } from './config.js';

const SOURCE_STORAGE_KEYS = {
  crit_source: 'cf.critSource',
  fumbleType: 'cf.fumbleType',
};

function readStoredSource(selectId) {
  try {
    return localStorage.getItem(SOURCE_STORAGE_KEYS[selectId]);
  } catch (e) {
    return null;
  }
}

function writeStoredSource(selectId, value) {
  try {
    localStorage.setItem(SOURCE_STORAGE_KEYS[selectId], value);
  } catch (e) { /* ignore quota/privacy errors */ }
}

function optionLabel(selectEl) {
  const opt = selectEl.options[selectEl.selectedIndex];
  return opt ? opt.textContent : selectEl.value;
}

function updateSummaryText(summaryEl, selectEl) {
  if (!summaryEl || !selectEl) return;
  const nameEl = summaryEl.querySelector('[data-source-name]');
  if (nameEl) nameEl.textContent = optionLabel(selectEl);
}

function setChooserOpen(chooserEl, summaryEl, changeBtn, open) {
  if (!chooserEl || !summaryEl) return;
  chooserEl.classList.toggle('is-open', open);
  summaryEl.classList.toggle('is-hidden', open);
  if (changeBtn) changeBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
}

export function initSourceDisclosure() {
  ['crit_source', 'fumbleType'].forEach(selectId => {
    const selectEl = document.getElementById(selectId);
    if (!selectEl) return;
    const stored = readStoredSource(selectId);
    if (stored) {
      const exists = Array.from(selectEl.options).some(o => o.value === stored);
      if (exists) selectEl.value = stored;
    }
  });

  document.querySelectorAll('.source-change-btn').forEach(btn => {
    const chooserEl = document.getElementById(btn.dataset.chooser);
    const summaryEl = document.getElementById(btn.dataset.summary);
    btn.addEventListener('click', () => {
      setChooserOpen(chooserEl, summaryEl, btn, true);
      const select = chooserEl?.querySelector('select');
      if (select) select.focus();
    });
  });

  const critSelect = document.getElementById('crit_source');
  const fumbleSelect = document.getElementById('fumbleType');
  const critSummary = document.getElementById('crit-source-summary');
  const fumbleSummary = document.getElementById('fumble-type-summary');
  const critChooser = document.getElementById('crit-source-chooser');
  const fumbleChooser = document.getElementById('fumble-type-chooser');
  const critChangeBtn = critSummary?.querySelector('.source-change-btn');
  const fumbleChangeBtn = fumbleSummary?.querySelector('.source-change-btn');

  if (critSelect) {
    updateSummaryText(critSummary, critSelect);
    critSelect.addEventListener('change', () => {
      writeStoredSource('crit_source', critSelect.value);
      updateSummaryText(critSummary, critSelect);
    });
  }
  if (fumbleSelect) {
    updateSummaryText(fumbleSummary, fumbleSelect);
    fumbleSelect.addEventListener('change', () => {
      writeStoredSource('fumbleType', fumbleSelect.value);
      updateSummaryText(fumbleSummary, fumbleSelect);
    });
  }
}

export function closeAllChoosers() {
  document.querySelectorAll('.source-change-btn').forEach(btn => {
    const chooserEl = document.getElementById(btn.dataset.chooser);
    const summaryEl = document.getElementById(btn.dataset.summary);
    setChooserOpen(chooserEl, summaryEl, btn, false);
  });
}

export function toggleAttackType() {
  const fumbleTypeSelect = document.getElementById('fumbleType');
  const selectedFumbleType = fumbleTypeSelect.value;
  const attackTypeContainer = document.getElementById('attack-type-container');
  const attackTypeSelect = document.getElementById('attackType');
  const rollType = document.querySelector('input[name="roll_type"]:checked').value;
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
    } else if (selectedFumbleType === "Fury & Folly") {
      newOptions = [{ value: "Physical", text: "Physical" }, { value: "Elemental", text: "Elemental" }, { value: "Magical", text: "Magical" }];
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

export function toggleFields() {
  const rollType = document.querySelector('input[name="roll_type"]:checked').value;
  const critFields = document.getElementById('crit-fields');
  const fumbleTypeContainer = document.getElementById('fumble-type-container');
  const attackTypeContainer = document.getElementById('attack-type-container');
  const critSourceContainer = document.getElementById('crit-source-container');
  const currentCritSourceInfoIcon = document.getElementById('crit_source_info_icon');
  const currentFumbleTypeInfoIcon = document.getElementById('fumble_type_info_icon');
  const critSummary = document.getElementById('crit-source-summary');
  const fumbleSummary = document.getElementById('fumble-type-summary');
  if (rollType === 'fumble') {
    critFields.style.display = 'none';
    critSourceContainer.style.display = 'none';
    if(currentCritSourceInfoIcon) currentCritSourceInfoIcon.style.display = 'none';
    fumbleTypeContainer.style.display = 'block';
    if(currentFumbleTypeInfoIcon) currentFumbleTypeInfoIcon.style.display = 'inline-block';
    if (critSummary) critSummary.classList.remove('is-active');
    if (fumbleSummary) fumbleSummary.classList.add('is-active');
    toggleAttackType();
  } else { // crit
    critFields.style.display = 'block';
    critSourceContainer.style.display = 'block';
    if(currentCritSourceInfoIcon) currentCritSourceInfoIcon.style.display = 'inline-block';
    fumbleTypeContainer.style.display = 'none';
    if(currentFumbleTypeInfoIcon) currentFumbleTypeInfoIcon.style.display = 'none';
    attackTypeContainer.style.display = 'none';
    if (critSummary) critSummary.classList.add('is-active');
    if (fumbleSummary) fumbleSummary.classList.remove('is-active');
    updateDamageAndMagicTypes();
  }
}

function damageTypeDisplayName(type) {
  if (type.includes(':')) {
    const suffix = type.split(':')[1];
    return suffix.charAt(0).toUpperCase() + suffix.slice(1);
  }
  return type.charAt(0).toUpperCase() + type.slice(1);
}

export function updateDamageAndMagicTypes() {
  const critSource = document.getElementById('crit_source').value;
  const damageTypeSelect = document.getElementById('damage_type');
  damageTypeSelect.innerHTML = '';
  const sourceData = CONFIG.critSourceDamageTypes[critSource];
  if (sourceData) {
    if (sourceData.optgroups) {
      for (const [groupLabel, types] of Object.entries(sourceData.optgroups)) {
        const group = document.createElement('optgroup');
        group.label = groupLabel;
        types.forEach(type => {
          const option = document.createElement('option');
          option.value = type;
          option.textContent = damageTypeDisplayName(type);
          group.appendChild(option);
        });
        damageTypeSelect.appendChild(group);
      }
    } else {
      sourceData.options.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = damageTypeDisplayName(type);
        damageTypeSelect.appendChild(option);
      });
    }
  } else {
    const option = document.createElement('option');
    option.value = "";
    option.textContent = "Select Crit Source";
    damageTypeSelect.appendChild(option);
  }
}