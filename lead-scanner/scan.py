"""
Local business website scanner.

Finds businesses in a radius around a center point, grades each one's website
(or lack of one), and writes a CSV sorted worst-first — i.e. the best leads
for someone pitching web work.

Usage:
    python scan.py                          # uses defaults from CONFIG below
    python scan.py --radius-km 20           # override radius
    python scan.py --categories personal    # only one category group
    python scan.py --dry-run                # skip website fetches, just list

The Google Places API key is read from GOOGLE_PLACES_API_KEY (env var or .env).
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Iterable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


# --------------------------------------------------------------------------- #
# CONFIG — safe to edit
# --------------------------------------------------------------------------- #

# 209 3rd St South, Martensville SK — approximate geocode
CENTER_LAT = 52.2911
CENTER_LNG = -106.6683
DEFAULT_RADIUS_KM = 35.0

# Google Places "included types" grouped by the trades chosen during setup.
# https://developers.google.com/maps/documentation/places/web-service/place-types
CATEGORIES: dict[str, list[str]] = {
    "personal": [
        "hair_salon",
        "barber_shop",
        "beauty_salon",
        "nail_salon",
        "spa",
    ],
    "trades": [
        "plumber",
        "electrician",
        "roofing_contractor",
        "painter",
        "general_contractor",
        "locksmith",
        "moving_company",
    ],
    "food_retail": [
        "restaurant",
        "cafe",
        "bakery",
        "meal_takeaway",
        "store",
        "florist",
    ],
}

# Google Places Nearby Search caps at radius 50 km AND 20 results per call.
# To sweep a large area properly we tile the region with smaller circles and
# dedupe by place_id afterward.
TILE_RADIUS_KM = 5.0

# When fetching each business's website to grade it
HTTP_TIMEOUT_SEC = 8
USER_AGENT = "Mozilla/5.0 (compatible; DadsBarbershopLeadScanner/1.0)"

OUTPUT_CSV = "leads.csv"


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass
class Business:
    place_id: str
    name: str
    address: str
    phone: str
    website: str
    category: str
    lat: float
    lng: float
    distance_km: float
    # Filled in during grading:
    site_score: int = 0  # 0 = pristine, higher = worse (better lead)
    site_issues: list[str] = field(default_factory=list)
    site_platform: str = ""

    def issues_str(self) -> str:
        return "; ".join(self.site_issues)


# --------------------------------------------------------------------------- #
# Geometry helpers
# --------------------------------------------------------------------------- #


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def tile_centers(
    center_lat: float, center_lng: float, radius_km: float, tile_radius_km: float
) -> list[tuple[float, float]]:
    """Hex-ish grid of tile centers covering a disk of `radius_km`.

    Spacing = tile_radius so adjacent circles overlap generously — no gaps.
    """
    spacing_km = tile_radius_km
    km_per_deg_lat = 111.32
    km_per_deg_lng = 111.32 * math.cos(math.radians(center_lat))

    tiles: list[tuple[float, float]] = []
    steps = int(math.ceil(radius_km / spacing_km)) + 1
    for iy in range(-steps, steps + 1):
        for ix in range(-steps, steps + 1):
            dy_km = iy * spacing_km
            # offset every other row for hex packing
            dx_km = ix * spacing_km + (spacing_km / 2 if iy % 2 else 0)
            lat = center_lat + dy_km / km_per_deg_lat
            lng = center_lng + dx_km / km_per_deg_lng
            if haversine_km(center_lat, center_lng, lat, lng) <= radius_km:
                tiles.append((lat, lng))
    return tiles


# --------------------------------------------------------------------------- #
# Google Places (New) — Nearby Search
# --------------------------------------------------------------------------- #

PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACES_FIELDS = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.nationalPhoneNumber,"
    "places.websiteUri,"
    "places.location,"
    "places.primaryType"
)


def search_places(
    api_key: str,
    lat: float,
    lng: float,
    radius_km: float,
    included_types: list[str],
) -> list[dict]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": PLACES_FIELDS,
    }
    body = {
        "includedTypes": included_types,
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_km * 1000,
            }
        },
    }
    try:
        r = requests.post(PLACES_URL, headers=headers, json=body, timeout=15)
    except requests.RequestException as exc:
        print(f"  ! Places request failed: {exc}", file=sys.stderr)
        return []
    if r.status_code != 200:
        print(f"  ! Places {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return []
    return r.json().get("places", [])


def gather_businesses(
    api_key: str,
    center_lat: float,
    center_lng: float,
    radius_km: float,
    category_keys: list[str],
) -> list[Business]:
    tiles = tile_centers(center_lat, center_lng, radius_km, TILE_RADIUS_KM)
    print(f"Sweeping {len(tiles)} tiles across {radius_km} km …")

    seen: dict[str, Business] = {}
    total_calls = 0

    for cat_key in category_keys:
        types = CATEGORIES[cat_key]
        print(f"\n[{cat_key}] {len(types)} type(s) × {len(tiles)} tiles")
        for t_idx, (lat, lng) in enumerate(tiles, 1):
            for included_type in types:
                total_calls += 1
                places = search_places(api_key, lat, lng, TILE_RADIUS_KM, [included_type])
                for p in places:
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    loc = p.get("location", {})
                    plat = loc.get("latitude", 0.0)
                    plng = loc.get("longitude", 0.0)
                    dist = haversine_km(center_lat, center_lng, plat, plng)
                    if dist > radius_km:
                        continue
                    seen[pid] = Business(
                        place_id=pid,
                        name=(p.get("displayName") or {}).get("text", ""),
                        address=p.get("formattedAddress", ""),
                        phone=p.get("nationalPhoneNumber", ""),
                        website=p.get("websiteUri", "") or "",
                        category=p.get("primaryType", included_type),
                        lat=plat,
                        lng=plng,
                        distance_km=round(dist, 2),
                    )
                # Small courtesy pause so we don't slam the API
                time.sleep(0.05)
            print(f"  tile {t_idx}/{len(tiles)} — {len(seen)} unique so far")

    print(f"\nDone. {total_calls} Places calls, {len(seen)} unique businesses.")
    return list(seen.values())


# --------------------------------------------------------------------------- #
# Website grading — the "who's a good lead" logic
# --------------------------------------------------------------------------- #

TEMPLATE_FINGERPRINTS = {
    # generator meta tag / URL pattern -> friendly platform name
    "wix.com": "Wix",
    "wixstatic": "Wix",
    "squarespace": "Squarespace",
    "godaddy": "GoDaddy Website Builder",
    "godaddysites": "GoDaddy Website Builder",
    "weebly": "Weebly",
    "site123": "SITE123",
    "webs.com": "Webs.com",
    "jimdo": "Jimdo",
    "wordpress": "WordPress",  # not damning on its own but useful signal
    "yolasite": "Yola",
    "webnode": "Webnode",
    "webstarts": "WebStarts",
    "duda.co": "Duda",
    "bookmark.com": "Bookmark",
}

FACEBOOK_ONLY_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "fb.me"}
INSTAGRAM_ONLY_HOSTS = {"instagram.com", "www.instagram.com"}


def grade_website(biz: Business) -> None:
    """Mutate `biz` in place with a score + list of issues.

    Higher score = worse website = better sales lead.
    """
    url = biz.website.strip()

    if not url:
        biz.site_score = 100
        biz.site_issues.append("no website listed")
        return

    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()

    if host in FACEBOOK_ONLY_HOSTS:
        biz.site_score = 90
        biz.site_platform = "Facebook page only"
        biz.site_issues.append("Facebook page used as website")
        return
    if host in INSTAGRAM_ONLY_HOSTS:
        biz.site_score = 90
        biz.site_platform = "Instagram page only"
        biz.site_issues.append("Instagram page used as website")
        return

    score = 0
    issues: list[str] = []
    platform = ""

    # HTTPS check
    if parsed.scheme != "https":
        score += 25
        issues.append("no HTTPS")

    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT_SEC,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        biz.site_score = 80
        biz.site_issues.append(f"site unreachable ({type(exc).__name__})")
        return

    if r.status_code >= 400:
        biz.site_score = 80
        biz.site_issues.append(f"HTTP {r.status_code}")
        return

    html = r.text
    html_lower = html.lower()

    # Template / builder fingerprinting
    for fp, name in TEMPLATE_FINGERPRINTS.items():
        if fp in html_lower:
            platform = name
            # WordPress by itself isn't a bad website; the free builders are.
            if name != "WordPress":
                score += 25
                issues.append(f"built on {name}")
            else:
                issues.append("WordPress (check theme quality)")
            break

    soup = BeautifulSoup(html, "html.parser")

    # Mobile viewport
    if not soup.find("meta", attrs={"name": "viewport"}):
        score += 20
        issues.append("no mobile viewport tag")

    # Page weight / substance — a real site is usually >30 KB of HTML
    if len(html) < 5000:
        score += 15
        issues.append("very small page (<5 KB)")

    # Title tag
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")
    if not title:
        score += 10
        issues.append("missing <title>")
    elif len(title) < 5:
        score += 5
        issues.append("weak <title>")

    # Meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if not meta_desc or not (meta_desc.get("content") or "").strip():
        score += 5
        issues.append("no meta description")

    # Under-construction / template placeholder text
    placeholders = [
        "lorem ipsum",
        "coming soon",
        "under construction",
        "site not published",
        "this domain",
        "buy this domain",
    ]
    for phrase in placeholders:
        if phrase in html_lower:
            score += 20
            issues.append(f"placeholder text: '{phrase}'")
            break

    # Copyright year staleness — a stale footer year is a strong "abandoned" signal
    years = re.findall(r"©\s*(20\d{2})", html)
    if years:
        newest = max(int(y) for y in years)
        current_year = time.gmtime().tm_year
        if newest < current_year - 2:
            score += 10
            issues.append(f"stale copyright ({newest})")

    biz.site_score = score
    biz.site_issues = issues
    biz.site_platform = platform


# --------------------------------------------------------------------------- #
# CSV output
# --------------------------------------------------------------------------- #


def write_csv(businesses: list[Business], path: str) -> None:
    fields = [
        "site_score",
        "name",
        "category",
        "distance_km",
        "phone",
        "address",
        "website",
        "site_platform",
        "site_issues",
        "place_id",
        "lat",
        "lng",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for b in businesses:
            row = asdict(b)
            row["site_issues"] = b.issues_str()
            writer.writerow({k: row[k] for k in fields})


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", type=float, default=CENTER_LAT)
    parser.add_argument("--lng", type=float, default=CENTER_LNG)
    parser.add_argument("--radius-km", type=float, default=DEFAULT_RADIUS_KM)
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=list(CATEGORIES.keys()),
        default=list(CATEGORIES.keys()),
        help="Which category groups to sweep.",
    )
    parser.add_argument("--out", default=OUTPUT_CSV)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip fetching each website — faster, only shows listings.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Grade at most this many businesses (0 = no limit).",
    )
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if not api_key:
        print(
            "ERROR: GOOGLE_PLACES_API_KEY is not set.\n"
            "Copy .env.example to .env and paste your key, or export the env var.",
            file=sys.stderr,
        )
        return 1

    businesses = gather_businesses(
        api_key=api_key,
        center_lat=args.lat,
        center_lng=args.lng,
        radius_km=args.radius_km,
        category_keys=args.categories,
    )

    if not args.dry_run:
        to_grade = businesses if args.limit == 0 else businesses[: args.limit]
        print(f"\nGrading {len(to_grade)} websites …")
        for i, biz in enumerate(to_grade, 1):
            grade_website(biz)
            if i % 25 == 0:
                print(f"  graded {i}/{len(to_grade)}")

    businesses.sort(key=lambda b: (-b.site_score, b.distance_km))
    write_csv(businesses, args.out)
    print(f"\nWrote {len(businesses)} rows to {args.out} (sorted worst-first).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
