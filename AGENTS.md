# Repository Guidelines

## Project Structure & Module Organization

This repository contains a static, interactive Japan travel itinerary generated with Python and Folium.

- `japan_interactive_map.py` is the Japan itinerary source and generates `japan.html`.
- `index.html`, `manifest.json`, and `sw.js` provide the static-site/PWA entry points.
- `japan_route_cache.json` caches external routing responses.

Treat generated HTML as checked-in build output. When changing a generator, regenerate and review its corresponding HTML in the same commit.

## Build, Test, and Development Commands

Use Python 3.11, matching CI:

```bash
python -m pip install folium polyline requests
python japan_interactive_map.py
python -m py_compile japan_interactive_map.py
python -m http.server 8000
```

The generator commands rebuild the map pages and may contact Open-Meteo and Valhalla when cached data is absent or stale. `py_compile` provides a quick syntax check. The HTTP server supports a browser smoke test at `http://localhost:8000/`; verify map rendering, layer toggles, popups, itinerary filters, and mobile layout.

## Coding Style & Naming Conventions

Follow existing Python conventions: four-space indentation, `snake_case` functions and variables, and `UPPER_SNAKE_CASE` constants. Keep itinerary data grouped by day and preserve the tuple/dictionary schemas documented beside each collection. Prefer small helper functions for repeated HTML or map behavior. Use descriptive lowercase filenames, with generated caches prefixed by the destination (for example, `japan_route_cache.json`).

No formatter or linter is configured. Keep diffs focused, preserve UTF-8 accents and emoji, and avoid hand-editing large generated HTML when the generator can make the change.

## Testing Guidelines

There is no automated test framework or coverage threshold. For every change, run `py_compile`, regenerate the affected page, and perform the browser smoke test above. Confirm external-data failures fall back to cached content where applicable.

## Commit & Pull Request Guidelines

Recent commits use concise, imperative, outcome-focused subjects, such as `Drop redundant marker tooltips...`.

Pull requests should summarize the itinerary or UI change, list validation performed, and identify regenerated files. Link relevant issues and include screenshots for visible layout or map changes. Do not mix unrelated destination updates.
