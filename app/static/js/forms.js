// Form handling and UI toggle functions
import { CONFIG } from './config.js';

export function toggleAttackType() {
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