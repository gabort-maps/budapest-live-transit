# Budapest Live Transit

Live map of Budapest public transport vehicles, by [Parallax Insight](https://parallaxinsight.eu/).

**Map:** https://gabort-maps.github.io/budapest-live-transit/

## How it works

- `index.html` is the whole map: base layers are built into the page, MapLibre GL JS 5.24.0 loads from jsDelivr.
- Every 10 seconds the page asks a small proxy (`bkk-proxy.gabortamas01.workers.dev/vehicles`) for current vehicle positions. The proxy calls BKK's FUTÁR API with a key held as a Cloudflare secret. **No API key is in this repository.**
- Vehicles glide between updates. Vehicles not in service (no route) are hidden by default.
- Metro is not in BKK's live feed.

## Sources

- Live vehicles: Data source: BKK Zrt., CC BY 4.0 (FUTÁR API). Independent; not produced or endorsed by BKK.
- Districts, Danube, main roads: © OpenStreetMap contributors (ODbL), via Budapest Map Library v2.13.
