# Crits & Fumbles 🎲💥

A Flask-based web app for generating critical hit and fumble results in Dungeons & Dragons. A vibe coding project.

## Features

- **Multiple Roll Types**: Critical hits and fumbles from various sources
- **Source Selection**: Choose from Sterling Vermin, Questionable Arcana, and u/BCoydog tables
- **Discord Integration**: Share roll results directly to Discord servers via configurable webhook URLs
- **Roll History**: View your previous rolls in the Chronicles
- **Responsive Design**: Works on desktop and mobile devices
- **Accessibility**: Screen reader support and keyboard navigation

## To Run Locally

1. Clone the repository and navigate to the project folder.
2. Create an `.env` file (not stored in git) and add:

```
FLASK_APP=app.app
FLASK_ENV=development
FLASK_DEBUG=1
```

3. Now to launch the app:

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
```

## Usage

1. **Select Roll Type**: Choose between Critical Hit or Fumble
2. **Choose Source**: Pick your preferred source material  
3. **Configure Options**: Select damage type, magic subtype, or attack type as needed
4. **Roll**: Click the lightning bolt button to generate your result
5. **Share to Discord** (optional): Configure a Discord webhook to share results directly to your server
6. **View History**: Click "📜 C&F Chronicles" to see your roll history

### Discord Integration

Configure Discord sharing by clicking the Discord button in the footer:
- Add your Discord webhook URL to enable sharing
- Generate shareable URLs that allow others to post to your Discord server  
- Share roll results directly to Discord with formatted messages

## Notes on the Sources

* [Critical Hits Revisited](https://sterlingvermin.wordpress.com/2016/09/27/critical-hits-revisited/) by Benjamin Huffman (crits only)
* [Questionable Arcana](https://growupandgame.com/dungeons-and-dragons/questionable-arcana/dnd-5e-crit-confirmed-critical-hit-charts-and-fumble-charts/) (crits & fumbles)
* [Reddit user u/Bcoydog](https://www.reddit.com/r/DnD/comments/1cuzgxf/critical_hit_fumble_d100_tables_with_51_results/) (crits & fumbles)

TODO: Add u/Bcoydog’s Knowledge Check Table (maybe?).

## Smack Down

_Deprecated. The Smack Down table has been removed for now, but may return someday!_ 

The first fumbles table is what we’ve been using in my current campaign and isn’t a fumble table at all. Instead, it’s the so-called “Smack Down Table or the ‘shit happens’ list,” which (as far as I can tell) can only be found on [DeviantArt](https://www.deviantart.com/pandabarbear/art/The-New-Smack-Down-Table-518745000). PandaBarBear (the user who posted the table) notes that it’s “based on Hack Masters Expanded smart ass smack down table,” which doesn’t exist (as far as I can tell).

[Issue 31 of “HackJournal”](https://kenzerco.com/product/hackjournal-31-pdf/?add-to-cart=4805) has a “Fumbles & Mishaps” table, which is more serious in nature and includes unfortunate fumble events like increased hypertension (!) and muscle pulls. It’s nothing at all like the table we’ve been using.

A more likely source of the “Smack Down Table” is found in [issue 128 of “Knights of the Dinner Table,”](https://kenzerco.com/product/knights-of-the-dinner-table-128/) which includes “The EXPANDED Smart Ass Smack Down Table” on page forty-one, created for DMs to dish out punishment to disruptive players:

> Guaranteed to make your players wet themselves in fright, or at least make you feel more like an evil over-lord punishing insubordinates.

The “Smack Down Table” from PandaBarBear uses some but not all of the same player punishments.

In any case, as I said, it’s not a fumble table at all. I've used it in the app because we’ve been using it in our game even before I joined, and it’s funny.