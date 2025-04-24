# Crits & Fumbles 🎲💥

A Flask-based web app for generating critical hit and fumble results in Dungeons & Dragons. A vibe coding project.

## To Run Locally

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
```

## Notes on the Sources

### Criticals

“[Critical Hits Revisited](https://sterlingvermin.wordpress.com/2016/09/27/critical-hits-revisited/)” by Benjamin Huffman

### Fumbles

The fumbles table we’ve been using in our campaign is not a fumble table at all. Instead, it’s the so-called “Smack Down Table or the ‘shit happens’ list,” which (as far as I can tell) can only be found on [DeviantArt](https://www.deviantart.com/pandabarbear/art/The-New-Smack-Down-Table-518745000). PandaBarBear (the user who posted the table) notes that it’s “based on Hack Masters Expanded smart ass smack down table,” which doesn’t exist (as far as I can tell).

[Issue 31 of “HackJournal”](https://kenzerco.com/product/hackjournal-31-pdf/?add-to-cart=4805) has a “Fumbles & Mishaps” table, which is more serious in nature and includes unfortunate fumble events like increased hypertension and muscle pulls. In any case, it’s nothing at all like the table we’ve been using.

A more likely source of the “Smack Down Table” is found in [issue 128 of “Knights of the Dinner Table,”](https://kenzerco.com/product/knights-of-the-dinner-table-128/) which includes “The EXPANDED Smart Ass Smack Down Table” on page forty-one, created for DMs to dish out punishment to disruptive players:

> Guaranteed to make your players wet themselves in fright, or at least make you feel more like an evil over-lord punishing insubordinates.

The “Smack Down Table” from PandaBarBear uses some but not all of the same player punishments.

In any case, as I said, it’s not a fumble table at all. I've used it in the app because we’ve been using it in our game even before I joined, and it’s funny.
