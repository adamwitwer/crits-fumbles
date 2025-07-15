// Configuration and constants
export const CONFIG = {
  // Data for Dynamic Dropdowns & Info Modals
  critSourceDamageTypes: {
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
  },

  sourceInfoTexts: {
    critSources: {
      "Sterling Vermin": "<a target='_blank' rel='noopener noreferrer' href='https://sterlingvermin.wordpress.com/2016/09/27/critical-hits-revisited/'>Critical Hits Revisited</a> offers d20 results with comprehensive damage types, including magic subtypes and insanities.",
      "Questionable Arcana": "These d100 critical hit tables from <a target='_blank' rel='noopener noreferrer' href='https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/'>Questionable Arcana</a> provide narrative and situational effects, often with a unique twist. They are broadly categorized (e.g., Weapon, Spell) and complemented by the QA fumble tables.",
      "BCoydog": "Reddit user u/BCoydog shared these critical hit tables in <a target='_blank' rel='noopener noreferrer' href='https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/'>the DnD subreddit</a>. Expect wild (but fair) outcomes for melee, ranged, and magic attacks, often with detailed descriptions and mechanical impacts. Accompanied by a fumble <span class='nowrap'>table</span>."
    },
    fumbleSources: {
      "Questionable Arcana": "The <a target='_blank' rel='noopener noreferrer' href='https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/'>Questionable Arcana</a> d100 fumble tables focus on the story consequences of fumbled weapon or spell attacks.",
      "BCoydog": "Reddit user u/BCoydog's <a target='_blank' rel='noopener noreferrer' href='https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/'>d100 fumble tables</a> feature humorous or challenging results for fumbled melee, ranged, or magic actions."
    }
  }
};