# Local Business Lead Scanner

Finds businesses within a 35 km radius of 209 3rd St South, Martensville SK,
grades each one's website (or lack of one), and writes a CSV sorted
worst-first — i.e. the best leads for someone selling web work.

## What it looks for

Each business gets a `site_score` from 0 (pristine site) upward. Higher is a
better lead. The signals it uses:

- **No website at all** — the strongest signal (score 100)
- **Facebook or Instagram page used as their "website"** (score 90)
- **Site unreachable / broken** (score 80)
- **Built on a free site builder** — Wix, GoDaddy, Weebly, SITE123, Jimdo, Yola, etc. (+25)
- **No HTTPS** (+25)
- **No mobile viewport tag** — will render unusably on phones (+20)
- **"Coming soon" / "under construction" / parked domain** (+20)
- **Very small page** (<5 KB of HTML — usually a template shell) (+15)
- **Missing `<title>` tag / weak title** (+10 / +5)
- **No meta description** (+5)
- **Stale copyright footer** (2+ years old — abandoned site) (+10)

WordPress is noted but doesn't hurt the score — plenty of good sites use it.

## Setup — one time

### 1. Install Python dependencies

```bash
cd lead-scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Get a Google Places API key (~5 min, free tier covers this easily)

Google gives every account a **$200/month free credit**. A full scan of a 35 km
radius costs roughly $5–15 depending on how many categories you include, so
you'll almost certainly stay under the free credit.

1. Go to <https://console.cloud.google.com/>. Sign in with a Google account.
2. Top bar → **Select a project** → **NEW PROJECT**. Name it anything
   (e.g. "lead-scanner"). Click **CREATE**.
3. Left menu → **APIs & Services** → **Library**. Search for
   **Places API (New)** and click **ENABLE**.
   (Enable the "Places API (New)" one — not the old "Places API".)
4. Left menu → **APIs & Services** → **Credentials** → **+ CREATE CREDENTIALS**
   → **API key**. Copy the key that appears.
5. Click the new key to edit it, then under **API restrictions** pick
   **Restrict key** and check **Places API (New)**. Save. This means if the key
   ever leaks, nobody can rack up charges on other Google services with it.
6. (Optional but wise.) Left menu → **Billing** → **Budgets & alerts** →
   **CREATE BUDGET**. Set a $25/month budget with an email alert at 50% and
   100%. Belt and suspenders.

### 3. Save your key locally

```bash
cp .env.example .env
# open .env and paste your key on the GOOGLE_PLACES_API_KEY= line
```

`.env` is gitignored — the key never gets committed or pushed anywhere.

## Run it

```bash
# From lead-scanner/, with the venv active:
python scan.py
```

Defaults: 35 km around 209 3rd St South, all three category groups, writes
`leads.csv` in the current folder.

### Useful flags

```bash
python scan.py --radius-km 20                 # smaller radius, faster + cheaper
python scan.py --categories personal          # only barbers/salons/spas
python scan.py --categories trades food_retail
python scan.py --dry-run                      # skip grading, just list businesses
python scan.py --limit 50                     # only grade the first 50 (test run)
python scan.py --out saskatoon.csv            # custom output file
```

### First-time sanity check

Before spending money on a full sweep, do a dry run:

```bash
python scan.py --radius-km 5 --categories personal --dry-run
```

That'll cost pennies and confirm your API key works and the tool centers on
the right point.

## Reading `leads.csv`

Open in Excel, Numbers, or Google Sheets. Rows are sorted with the biggest
opportunities (score 100 — no website at all) at the top. Key columns:

| Column          | What it means                                                       |
| --------------- | ------------------------------------------------------------------- |
| `site_score`    | Higher = worse website = better lead                                |
| `name`          | Business name                                                       |
| `category`      | Google's category, e.g. `plumber`, `barber_shop`, `restaurant`      |
| `distance_km`   | Straight-line distance from 209 3rd St South                        |
| `phone`         | Business phone (for outreach)                                       |
| `website`       | Current site URL, if any                                            |
| `site_platform` | Detected builder (Wix, GoDaddy, etc.) — nice conversation opener    |
| `site_issues`   | Semicolon-separated list of specific problems found                 |

## Costs — rough numbers

Google Places New charges per SKU (Nearby Search = $32 / 1000 calls, first
$200/month free).

A full sweep of a 35 km radius with all three category groups is roughly
**~700–900 API calls**, or $22–29 gross before the free credit. In practice
you pay $0 unless you're already using Google Cloud heavily for other things.

The website-grading step doesn't cost anything — those are plain HTTP fetches
from the internet.

## Re-running

Numbers change slowly. Re-running monthly is plenty. If you want to track how
often a lead's site actually gets updated, save each run to a dated file:

```bash
python scan.py --out "leads-$(date +%Y-%m).csv"
```

## What this scanner does NOT do

- **Doesn't rank leads by revenue potential** — a food truck and a machine
  shop both look the same to it. Sort by category yourself in the CSV.
- **Doesn't detect broken JavaScript sites well** — it fetches raw HTML, so
  a fancy React site that only renders in a headless browser looks tiny to it.
  Spot-check anything flagged "very small page" for a well-known brand.
- **Doesn't contact anyone.** That's on you.
