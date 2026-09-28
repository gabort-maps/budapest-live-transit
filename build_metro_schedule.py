"""Build metro.json: the scheduled metro trips (M1-M4) from BKK's public GTFS timetable.

Runs on GitHub Actions (see .github/workflows/deploy.yml) on every deploy and on the 1st and 15th
of each month, so the map always carries a current timetable. No API key: the GTFS zip is public.
Can also run locally:  python build_metro_schedule.py [path/to/budapest_gtfs.zip]

Output (compact JSON, a few hundred KB):
  build, start, end           GTFS feed_version and validity window (YYYYMMDD)
  dates    {YYYYMMDD: [service index, ...]}   which services run on each date
  lines    [[name, colour], ...]
  shapes   [[[lon, lat, dist], ...], ...]     line geometry with distance along it (GTFS units)
  stops    [name, ...]
  patterns [[shape, line, headsign, [[stop, dist, t_offset_s], ...]], ...]
  trips    [[pattern, service, start_s], ...]  start_s = seconds after service-day midnight (can exceed 86400)
Data source: BKK Zrt., CC BY 4.0
"""
import csv, io, json, sys, urllib.request, zipfile, datetime

URL = "https://go.bkk.hu/api/static/v1/public-gtfs/budapest_gtfs.zip"

def secs(t):
    h, m, s = (int(x) for x in t.split(":"))
    return h * 3600 + m * 60 + s

def main():
    if len(sys.argv) > 1:
        z = zipfile.ZipFile(sys.argv[1])
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "budapest-live-transit (GitHub Actions)"})
        z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req, timeout=300).read()))
    rows = lambda n: csv.DictReader(io.TextIOWrapper(z.open(n), encoding="utf-8-sig"))

    feed = next(rows("feed_info.txt"))
    routes = {r["route_id"]: r for r in rows("routes.txt") if r["route_type"] == "1"}
    line_ids = sorted(routes, key=lambda k: routes[k]["route_short_name"])
    lines = [[routes[k]["route_short_name"], routes[k]["route_color"]] for k in line_ids]
    trips = {t["trip_id"]: t for t in rows("trips.txt") if t["route_id"] in routes}

    # stop times for metro trips only
    st = {}
    for r in rows("stop_times.txt"):
        if r["trip_id"] in trips:
            st.setdefault(r["trip_id"], []).append(r)
    stop_ids = {r["stop_id"] for v in st.values() for r in v}
    stop_name = {s["stop_id"]: s["stop_name"] for s in rows("stops.txt") if s["stop_id"] in stop_ids}

    shape_ids = {t["shape_id"] for t in trips.values()}
    shp = {}
    for r in rows("shapes.txt"):
        if r["shape_id"] in shape_ids:
            shp.setdefault(r["shape_id"], []).append((int(r["shape_pt_sequence"]), round(float(r["shape_pt_lon"]), 6),
                                                     round(float(r["shape_pt_lat"]), 6), round(float(r["shape_dist_traveled"] or 0), 1)))
    services = sorted({t["service_id"] for t in trips.values()})
    svc_i = {s: i for i, s in enumerate(services)}
    dates = {}
    for r in rows("calendar_dates.txt"):
        if r["service_id"] in svc_i and r["exception_type"] == "1":
            dates.setdefault(r["date"], []).append(svc_i[r["service_id"]])

    shape_list = sorted(shape_ids); shape_i = {s: i for i, s in enumerate(shape_list)}
    stops = sorted(set(stop_name.values())); stop_i = {n: i for i, n in enumerate(stops)}
    heads, head_i = [], {}
    patterns, pat_i, out_trips = [], {}, []
    for tid, t in trips.items():
        seq = sorted(st.get(tid, []), key=lambda r: int(r["stop_sequence"]))
        if len(seq) < 2: continue
        t0 = secs(seq[0]["departure_time"])
        h = t["trip_headsign"]
        if h not in head_i: head_i[h] = len(heads); heads.append(h)
        key = (t["shape_id"], t["route_id"], h, tuple((r["stop_id"], r["shape_dist_traveled"], secs(r["arrival_time"]) - t0) for r in seq))
        if key not in pat_i:
            pat_i[key] = len(patterns)
            patterns.append([shape_i[t["shape_id"]], line_ids.index(t["route_id"]), head_i[h],
                             [[stop_i[stop_name[r["stop_id"]]], round(float(r["shape_dist_traveled"] or 0), 1), secs(r["arrival_time"]) - t0] for r in seq]])
        out_trips.append([pat_i[key], svc_i[t["service_id"]], t0])

    out = {"build": feed["feed_version"], "start": feed["feed_start_date"], "end": feed["feed_end_date"],
           "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "source": "Data source: BKK Zrt., CC BY 4.0 (GTFS timetable)",
           "dates": dates, "lines": lines, "headsigns": heads, "stops": stops,
           "shapes": [[[p[1], p[2], p[3]] for p in sorted(shp[s])] for s in shape_list],
           "patterns": patterns, "trips": sorted(out_trips, key=lambda x: x[2])}
    with open("metro.json", "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
    print(f"metro.json: build {out['build']}, {out['start']}-{out['end']}, {len(out_trips)} trips, "
          f"{len(patterns)} patterns, {len(shape_list)} shapes, {len(stops)} stations")

if __name__ == "__main__":
    main()
