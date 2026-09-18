"""
Fetch canonical study-area OSM data (map + candidate POIs) for SUMO.

Downloads:
  - full OSM map (nodes/ways/relations) for the bbox -> sim/sumo/area.osm.xml
  - candidate hospitals / bridges / industrial POIs -> sim/sumo/osm_pois.json

Uses only the standard library so it runs before SUMO is installed.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator.geo import bbox_from_center  # noqa: E402

CENTER = (31.30377, 120.59981)   # facility centroid (D1/H1/V1/V2/V3/B1 midpoint)
WIDTH_KM, HEIGHT_KM = 3.2, 3.2   # cropped S0 extent (refined from 5x5 km)
OUT_MAP = ROOT / "sim" / "sumo" / "area.osm.xml"
OUT_POIS = ROOT / "sim" / "sumo" / "osm_pois.json"

OVERPASS_MAP = "https://overpass-api.de/api/map"
OVERPASS_INTERPRETER = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "ground-air-llm-cosim/1.0 (academic smoke test)"}


def http_post(url: str, data: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, data=data.encode("utf-8"), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def overpass_query(q: str) -> dict:
    payload = "data=" + urllib.parse.quote(q)
    raw = http_post(OVERPASS_INTERPRETER, payload)
    return json.loads(raw.decode("utf-8"))


def main() -> int:
    bbox = bbox_from_center(*CENTER, WIDTH_KM, HEIGHT_KM)
    s, w, n, e = bbox["south"], bbox["west"], bbox["north"], bbox["east"]
    print(f"bbox: south={s:.6f} north={n:.6f} west={w:.6f} east={e:.6f}")

    # 1) full map
    map_url = f"{OVERPASS_MAP}?bbox={w:.6f},{s:.6f},{e:.6f},{n:.6f}"
    print("downloading OSM map ...")
    map_bytes = http_get(map_url)
    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAP.write_bytes(map_bytes)
    print(f"  saved {OUT_MAP} ({len(map_bytes)} bytes)")

    # 2) POI queries
    pois = {}
    queries = {
        "hospitals": '[out:json][timeout:60];(node["amenity"~"hospital|clinic"]({s},{w},{n},{e}););out center;',
        "bridges_way": '[out:json][timeout:60];(way["bridge"="yes"]["highway"]({s},{w},{n},{e}););out center;',
        "industrial": '[out:json][timeout:60];(node["landuse"="industrial"]({s},{w},{n},{e});way["landuse"="industrial"]({s},{w},{n},{e});node["building"~"warehouse|industrial"]({s},{w},{n},{e}););out center;',
    }
    for key, tmpl in queries.items():
        q = tmpl.format(s=s, w=w, n=n, e=e)
        for attempt in range(3):
            try:
                res = overpass_query(q)
                pois[key] = res.get("elements", [])
                print(f"  {key}: {len(pois[key])} elements")
                break
            except Exception as ex:
                print(f"  {key} attempt {attempt+1} failed: {ex}")
                time.sleep(5)
        else:
            pois[key] = []

    OUT_POIS.write_text(json.dumps(pois, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved POIs -> {OUT_POIS}")

    # 3) summary
    print("\n=== HOSPITALS ===")
    for el in pois.get("hospitals", [])[:20]:
        t = el.get("tags", {})
        print(f"  {el.get('id')} lat={el.get('lat')} lon={el.get('lon')} name={t.get('name','?')} amenity={t.get('amenity')}")
    print("\n=== BRIDGES (way) ===")
    for el in pois.get("bridges_way", [])[:30]:
        t = el.get("tags", {})
        c = el.get("center", {})
        print(f"  {el.get('id')} lat={c.get('lat')} lon={c.get('lon')} name={t.get('name','?')} highway={t.get('highway')}")
    print("\n=== INDUSTRIAL ===")
    for el in pois.get("industrial", [])[:20]:
        t = el.get("tags", {})
        c = el.get("center", {})
        print(f"  {el.get('id')} lat={c.get('lat')} lon={c.get('lon')} name={t.get('name','?')} {t.get('landuse') or t.get('building')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
