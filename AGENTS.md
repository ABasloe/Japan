# Repository Guidelines

## Project Structure & Module Organization

This repository contains static, interactive travel itineraries generated with Python and Folium.

- `spain_interactive_map.py` is the source for the current Portugal/Spain itinerary and generates `spain.html`.
- `iceland_interactive_map.py` generates `iceland_interactive_map.html`; `iceland.html` is the related itinerary page.
- `index.html`, `manifest.json`, and `sw.js` provide the static-site/PWA entry points.
- `*_route_cache.json` and `*_weather_cache.json` cache external routing and forecast responses.
- `archive/` contains older Iceland generator outputs; do not update it as part of normal changes.
- `.github/workflows/refresh_weather.yml` regenerates and commits Spain weather data hourly.

Treat generated HTML as checked-in build output. When changing a generator, regenerate and review its corresponding HTML in the same commit.

## Build, Test, and Development Commands

Use Python 3.11, matching CI:

```bash
python -m pip install folium polyline requests
python spain_interactive_map.py
python iceland_interactive_map.py
python -m py_compile spain_interactive_map.py iceland_interactive_map.py
python -m http.server 8000
```

The generator commands rebuild the map pages and may contact Open-Meteo and Valhalla when cached data is absent or stale. `py_compile` provides a quick syntax check. The HTTP server supports a browser smoke test at `http://localhost:8000/`; verify map rendering, layer toggles, popups, itinerary filters, and mobile layout.

## Coding Style & Naming Conventions

Follow existing Python conventions: four-space indentation, `snake_case` functions and variables, and `UPPER_SNAKE_CASE` constants. Keep itinerary data grouped by day and preserve the tuple/dictionary schemas documented beside each collection. Prefer small helper functions for repeated HTML or map behavior. Use descriptive lowercase filenames, with destination-specific generated caches prefixed by the destination (for example, `spain_route_cache.json`).

No formatter or linter is configured. Keep diffs focused, preserve UTF-8 accents and emoji, and avoid hand-editing large generated HTML when the generator can make the change.

## Testing Guidelines

There is no automated test framework or coverage threshold. For every change, run `py_compile`, regenerate the affected page, and perform the browser smoke test above. Confirm external-data failures fall back to cached content where applicable.

## Commit & Pull Request Guidelines

Recent commits use concise, imperative, outcome-focused subjects, such as `Drop redundant marker tooltips...`. Automated weather commits use `🌤️ Auto-refresh Spain weather [YYYY-MM-DD HH:MM UTC]`; reserve that format for CI.

Pull requests should summarize the itinerary or UI change, list validation performed, and identify regenerated files. Link relevant issues and include screenshots for visible layout or map changes. Do not mix unrelated destination updates.
