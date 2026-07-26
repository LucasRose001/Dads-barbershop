#!/usr/bin/env python3
"""Scan a Google Maps area and export businesses that have no website listed.

Uses the Google Places API (v1). Set GOOGLE_MAPS_API_KEY in your environment.

Examples:
    # Barbershops within 3 km of a Martensville, SK address
    python3 find_businesses_without_websites.py \\
        --address "Martensville, SK" \\
        --radius 3000 \\
        --keyword "barber shop"

    # Explicit lat/lng
    python3 find_businesses_without_websites.py \\
        --lat 52.29 --lng -106.67 \\
        --radius 5000 \\
        --keyword "hair salon" \\
        --out leads.csv

    # Include businesses that DO have a website too (adds a column)
    python3 find_businesses_without_websites.py \\
        --address "Saskatoon, SK" --radius 4000 --keyword "restaurant" --all
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

PLACES_ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"
GEOCODE_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.websiteUri",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.googleMapsUri",
    "places.rating",
    "places.userRatingCount",
    "places.primaryType",
])


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def http_json(method: str, url: str, headers: dict, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        die(f"HTTP {e.code} from {url}\n{detail}")


def geocode(address: str, api_key: str) -> tuple[float, float]:
    q = urllib.parse.urlencode({"address": address, "key": api_key})
    result = http_json("GET", f"{GEOCODE_ENDPOINT}?{q}", headers={})
    if result.get("status") != "OK" or not result.get("results"):
        die(f"geocode failed for {address!r}: {result.get('status')} {result.get('error_message', '')}")
    loc = result["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def search_nearby(lat: float, lng: float, radius_m: float, keyword: str, api_key: str) -> list[dict]:
    if radius_m > 50000:
        die("radius must be <= 50000 meters (Places API limit)")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_m,
            }
        },
    }
    if keyword:
        # Places v1 uses `includedTypes` for taxonomy or a text query on searchText.
        # For a free-form keyword we use searchText instead of searchNearby.
        return search_text(lat, lng, radius_m, keyword, api_key)

    result = http_json("POST", PLACES_ENDPOINT, headers, body)
    return result.get("places", [])


def search_text(lat: float, lng: float, radius_m: float, keyword: str, api_key: str) -> list[dict]:
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK + ",nextPageToken",
    }
    all_places: list[dict] = []
    page_token: str | None = None

    for _ in range(3):  # up to 60 results across 3 pages
        body: dict = {
            "textQuery": keyword,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_m,
                }
            },
            "pageSize": 20,
        }
        if page_token:
            body["pageToken"] = page_token

        result = http_json("POST", url, headers, body)
        all_places.extend(result.get("places", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
        time.sleep(2)  # Google requires a short delay before pageToken is valid

    return all_places


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    loc = ap.add_mutually_exclusive_group(required=True)
    loc.add_argument("--address", help="Center address to geocode (e.g. 'Martensville, SK')")
    loc.add_argument("--lat", type=float, help="Center latitude (paired with --lng)")
    ap.add_argument("--lng", type=float, help="Center longitude (paired with --lat)")
    ap.add_argument("--radius", type=float, required=True, help="Search radius in meters (max 50000)")
    ap.add_argument("--keyword", required=True, help="What to search for (e.g. 'barber shop', 'salon')")
    ap.add_argument("--out", default="leads.csv", help="Output CSV path (default: leads.csv)")
    ap.add_argument("--all", action="store_true", help="Include businesses that DO have a website too")
    args = ap.parse_args()

    if args.lat is not None and args.lng is None:
        die("--lat requires --lng")

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        die("set GOOGLE_MAPS_API_KEY in your environment (see README)")

    if args.address:
        lat, lng = geocode(args.address, api_key)
        print(f"geocoded {args.address!r} -> {lat:.5f}, {lng:.5f}")
    else:
        lat, lng = args.lat, args.lng

    print(f"searching {args.keyword!r} within {args.radius:.0f} m of ({lat:.5f}, {lng:.5f})")
    places = search_text(lat, lng, args.radius, args.keyword, api_key)
    print(f"found {len(places)} places")

    rows = []
    for p in places:
        website = p.get("websiteUri") or ""
        if not args.all and website:
            continue
        rows.append({
            "name": (p.get("displayName") or {}).get("text", ""),
            "address": p.get("formattedAddress", ""),
            "phone": p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber") or "",
            "website": website,
            "has_website": "yes" if website else "no",
            "rating": p.get("rating", ""),
            "review_count": p.get("userRatingCount", ""),
            "type": p.get("primaryType", ""),
            "maps_url": p.get("googleMapsUri", ""),
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "name", "address", "phone", "website", "has_website",
            "rating", "review_count", "type", "maps_url",
        ])
        writer.writeheader()
        writer.writerows(rows)

    without = sum(1 for r in rows if r["has_website"] == "no")
    print(f"wrote {len(rows)} rows to {args.out} ({without} without a website)")


if __name__ == "__main__":
    main()
