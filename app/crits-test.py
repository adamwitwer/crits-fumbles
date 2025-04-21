import json

# Load the data
with open("crits_and_fumbles_v2.json") as f:
    data = json.load(f)

def resolve_roll(roll_input, table):
    roll = int(roll_input)
    for key in table:
        if '-' in key:
            start, end = map(int, key.split('-'))
            if start <= roll <= end:
                return table[key]
        elif str(roll) == key:
            return table[key]
    return "No result found for this roll."

def run_cli():
    print("Welcome to Crits & Fumbles Test App!")
    while True:
        roll_type = input("\nWhat type of roll? (crit, fumble, minor, major, insanity, quit): ").strip().lower()

        if roll_type == "quit":
            print("Goodbye!")
            break

        if roll_type == "crit":
            roll = input("Enter d20 roll (1-20): ")
            damage_type = input("Enter damage type (e.g., slashing, magic:fire): ").strip().lower()
            crit_table = data["crit_tables"].get(damage_type)
            if not crit_table:
                print("Invalid damage type.")
                continue
            print("\nResult:\n" + resolve_roll(roll, crit_table))

        elif roll_type == "fumble":
            roll = input("Enter d100 roll (1-100): ")
            print("\nResult:\n" + resolve_roll(roll, data["fumbles"]))

        elif roll_type == "minor":
            roll = input("Enter d20 roll (or range key): ")
            print("\nResult:\n" + resolve_roll(roll, data["minor_injuries"]))

        elif roll_type == "major":
            roll = input("Enter d20 roll (or range key): ")
            print("\nResult:\n" + resolve_roll(roll, data["major_injuries"]))

        elif roll_type == "insanity":
            roll = input("Enter d20 roll (1-20): ")
            print("\nResult:\n" + resolve_roll(roll, data["insanities"]))

        else:
            print("Unknown option. Please try again.")

if __name__ == "__main__":
    run_cli()

