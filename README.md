# Radar Dashboard (local copy)

A single-screen air-traffic radar in the style of an ATC scope. Live aircraft
around a location you choose, animated between data refreshes by projecting
each aircraft forward along its speed and heading (dead reckoning).

This is the take-away version of the hosted dashboard: two files, no accounts,
no API keys, nothing to install beyond Python 3.

## Files

- `index.html` — the whole dashboard (scope, controls, details panel)
- `server.py` — a tiny server using only the Python standard library. It
  serves the page and fetches the flight data, because browsers block direct
  calls to the feed (it sends no CORS headers).

## Run it

macOS (Terminal):

    cd radar-dashboard
    python3 server.py

Windows (PowerShell):

    cd radar-dashboard
    py server.py

Then open http://localhost:8765 in your browser.

Check it works: the status line at the top turns green — `LIVE · adsb.lol ·
updated …` — and aircraft appear on the scope. (No planes within your chosen
range also shows as LIVE, with "no aircraft in range".)

Stop it with Ctrl+C in the terminal.

Optional check of the data feed alone, while the server is running:

    curl "http://localhost:8765/api/point?lat=45.531&lon=-73.519&radiusKm=25"

That should print JSON starting with `{"ac": [...]}`.

## Using it

- **Set location** — type latitude/longitude and press the button, or use
  "Use my location" and let the browser locate you.
- **Range** — 5 to 100 km around the center point. Defaults: Longueuil,
  Québec (45.531, -73.519) at 25 km.
- **Click any target** (on the scope or in the traffic list) for callsign,
  registration, aircraft type, altitude, speed, heading, vertical rate,
  distance and bearing.
- The page refreshes the feed every 15 seconds while it's visible and
  animates smoothly in between.

## Data & politeness

Positions come from [adsb.lol](https://adsb.lol), a community ADS-B network,
with [adsb.fi](https://adsb.fi) as fallback — both free, no key. The free feed
allows roughly 500 requests/day per address; at one request every 15 seconds
that's about 2 hours of the dashboard open per day. Closing the tab stops all
requests. Aircraft show callsign, position, altitude and speed — not the
flight's origin/destination route.

## Put it on GitHub (optional)

Your GitHub login on your own machine is all that's needed — never send your
GitHub password or a token to anyone, including an AI assistant. Create a new
empty repository named `radar-dashboard` on github.com (signed in as
yourself), then in this folder:

    git init
    git add index.html server.py README.md
    git commit -m "Radar dashboard"
    git branch -M main
    git remote add origin git@github.com:sebagomez/radar-dashboard.git
    git push -u origin main
