# Repository Guidelines

## Project Overview
A single-screen air-traffic radar dashboard in ATC scope style. Live aircraft around a chosen location, animated between data refreshes via dead reckoning projection. Two files, no accounts, no API keys — Python 3 standard library only.

**Files:**
- `index.html` — complete dashboard (scope canvas, controls, details panel)
- `server.py` — tiny HTTP server serving HTML and proxying ADS-B feed (browsers block direct calls — no CORS headers on feeds)

**Data source:** adsb.lol (primary), adsb.fi (fallback) — free community ADS-B networks, ~500 requests/day per IP.

## Architecture & Data Flow
```
Browser (index.html) → /api/point → server.py → adsb.lol / adsb.fi → JSON → server.py → Browser
```

**Data flow:**
1. Browser polls `/api/point?lat=X&lon=Y&radiusKm=Z` every 15s (when tab visible)
2. `server.py` fetches from adsb.lol (converts km → nautical miles), falls back to adsb.fi; responses are cached 10s per location/range, and if both feeds fail the last good response is served (source marked `(stale)`) for up to 5 min
3. Response includes `X-Data-Source` header (`adsb.lol` or `adsb.fi`)
4. Browser ingests aircraft list, projects positions forward via dead reckoning between polls
5. Canvas renders at 60fps via `requestAnimationFrame`; side panel updates every 5s

**State (`index.html`):**
```js
const state = {
  center: { lat, lon },    // map center
  radiusKm: 25,            // range ring radius
  aircraft: Map<hex, rec>, // tracked aircraft
  selected: null,          // selected aircraft hex
  lastOk: null,            // last successful poll timestamp
  source: null             // data source name
};
```

## Key Directories
Single-file project — no subdirectories. All code in:
- `server.py` — Python 3.10+ (uses `ThreadingHTTPServer`, `urllib`)
- `index.html` — vanilla HTML/CSS/JS (ES2017+), no build step

## Development Commands
```bash
# Run server (default port 8765)
python3 server.py

# Custom port
python3 server.py 9000

# Test API directly (while server running)
curl "http://localhost:8765/api/point?lat=45.531&lon=-73.519&radiusKm=25"

# Open dashboard
open http://localhost:8765
```

**No package manager, no build, no lint, no test suite.**

## Code Conventions & Common Patterns

### Python (`server.py`)
- Standard library only — no dependencies
- `ThreadingHTTPServer` for concurrent requests
- Quiet logging: `log_message` overridden to suppress default output
- Error handling: try/except with graceful fallback (adsb.lol → adsb.fi)
- Input validation: lat/lon bounds, radius 0–500 km
- Type hints: absent (kept minimal)

### JavaScript (`index.html` inline)
- `'use strict'`
- Module-level state object (`state`), no classes
- Pure functions for geo math (`destPoint`, `haversineKm`, `bearingDeg`, `enuKm`, `applyEnu`)
- Dead reckoning: `projectedPos(rec, now)` projects from last fix using ground speed + track, capped at 20s past the fix (`MAX_PROJECT_MS`) so a slow refresh cannot project targets off the scope
- Smooth blending on new fixes: `blendE`/`blendN`/`blendT` decay over ~1s to avoid teleports
- Canvas rendering: `requestAnimationFrame` loop, 60fps
- Panel rendering: `setInterval(renderPanel, 5000)` for fresh distances
- Polling: `setInterval(poll, 15000)` + `document.hidden` check
- Spotter watchlist: `WATCH_TYPES` maps ICAO type codes (the feed's `t` field) to why an aircraft is interesting; matches get an amber pulsing ring on the scope, a ★ in the traffic list, and a one-time banner announcement per visit (tracked in `state.announced`)
- No external libraries, no bundler

### CSS (inline `<style>`)
- CSS custom properties for theme (`--bg`, `--panel`, `--line`, `--txt`, `--dim`, `--bright`, `--amber`, `--red`)
- Monospace font stack via `--mono`
- Mobile responsive: `<760px` stacks sidebar below canvas

## Important Files

| File | Purpose |
|------|---------|
| `server.py` | HTTP server + ADS-B proxy |
| `index.html` | Complete dashboard UI + logic |
| `README.md` | Usage docs |

**Entry points:**
- `server.py:85` — `if __name__ == "__main__":` starts server
- `index.html:429` — `fitCanvas(); poll(); setInterval(poll, POLL_MS); requestAnimationFrame(draw);`

**Key functions:**
- `server.py:get_traffic(lat, lon, radius_km)` — fetches from adsb.lol/adsb.fi
- `index.html:ingest(list)` — processes aircraft data, handles blending
- `index.html:projectedPos(rec, now)` — dead reckoning projection
- `index.html:draw(now)` — canvas render loop
- `index.html:renderPanel()` — side panel update

## Runtime/Tooling Preferences
- **Python:** 3.10+ (standard library only)
- **Browser:** any modern (ES2017+, Canvas 2D, fetch, geolocation)
- **No Node, no Bun, no npm, no build tools**
- **Editor:** any — single-file simplicity

## Testing & QA
No formal test suite. Manual verification:
1. Start `python3 server.py`
2. Open `http://localhost:8765`
3. Verify status line turns green: `LIVE · adsb.lol · updated …`
4. Aircraft appear on scope, clickable for details
5. Test API: `curl "http://localhost:8765/api/point?lat=45.531&lon=-73.519&radiusKm=25"` → JSON with `{"ac": [...]}`
6. Test geolocation button, range selector, manual refresh
7. Close tab → requests stop (check server logs if needed)

**Edge cases to verify:**
- No aircraft in range → "no aircraft in range" (still LIVE)
- Feed error → status red, error message suggests checking `server.py` running
- Page hidden → polling pauses (`document.hidden` check)
- Rapid turns → blip drifts until next fix (by design, noted in footer)