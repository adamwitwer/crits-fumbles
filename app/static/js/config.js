// Configuration and constants
export const CONFIG = {
  // Data for Dynamic Dropdowns & Info Modals
  critSourceDamageTypes: {
    "Sterling Vermin": {
      options: [
        "bludgeoning", "piercing", "slashing",
        "magic:acid", "magic:cold", "magic:fire", "magic:force",
        "magic:lightning", "magic:necrotic", "magic:poison",
        "magic:psychic", "magic:radiant", "magic:thunder"
      ],
      optgroups: {
        "Physical": ["bludgeoning", "piercing", "slashing"],
        "Magic": [
          "magic:acid", "magic:cold", "magic:fire", "magic:force",
          "magic:lightning", "magic:necrotic", "magic:poison",
          "magic:psychic", "magic:radiant", "magic:thunder"
        ]
      }
    },
    "Questionable Arcana": { options: ["weapon", "spell"] },
    "BCoydog": { options: ["melee", "ranged", "magic"] },
    "Fury & Folly": {
      options: [
        "bludgeoning", "slashing", "piercing",
        "acid", "cold", "fire", "lightning", "thunder",
        "force", "necrotic", "poison", "psychic", "radiant"
      ],
      optgroups: {
        "Physical":  ["bludgeoning", "slashing", "piercing"],
        "Elemental": ["acid", "cold", "fire", "lightning", "thunder"],
        "Magic":     ["force", "necrotic", "poison", "psychic", "radiant"]
      }
    }
  },

  sourceInfoTexts: {
    critSources: {
      "Fury & Folly": "The Crits &amp; Fumbles house system pairs <span class='nowrap'>damage-type\u2013specific</span> critical hits with <span class='nowrap'>condition-driven</span> effects and a complementary fumbles table.",
      "Sterling Vermin": "<a target='_blank' rel='noopener noreferrer' href='https://sterlingvermin.wordpress.com/2016/09/27/critical-hits-revisited/'>Critical Hits Revisited</a> offers d20 results with comprehensive damage types, including magic subtypes and insanities.",
      "Questionable Arcana": "These d100 critical hit tables from <a target='_blank' rel='noopener noreferrer' href='https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/'>Questionable Arcana</a> provide narrative and situational effects, often with a unique twist. They are broadly categorized (e.g., Weapon, Spell) and complemented by the QA fumble tables.",
      "BCoydog": "Reddit user u/BCoydog shared these critical hit tables in <a target='_blank' rel='noopener noreferrer' href='https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/'>the DnD subreddit</a>. Expect wild (but fair) outcomes for melee, ranged, and magic attacks, often with detailed descriptions and mechanical impacts. Accompanied by a fumble <span class='nowrap'>table</span>."
    },
    fumbleSources: {
      "Fury & Folly": "The Crits &amp; Fumbles house system pairs damage-type\u2013specific critical hits with condition-driven effects and a complementary fumbles table\u2014because every moment of fury deserves the possibility of folly.",
      "Questionable Arcana": "The <a target='_blank' rel='noopener noreferrer' href='https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/'>Questionable Arcana</a> d100 fumble tables focus on the story consequences of fumbled weapon or spell attacks.",
      "BCoydog": "Reddit user u/BCoydog's <a target='_blank' rel='noopener noreferrer' href='https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/'>d100 fumble tables</a> feature humorous or challenging results for fumbled melee, ranged, or magic actions."
    }
  }
};