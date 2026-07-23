# Tools

Utility scripts for the shop owner. Not part of the deployed site.

## `find_businesses_without_websites.py`

Scans a Google Maps area and exports a CSV of nearby businesses, flagging
which ones don't have a website listed on their Google Business Profile —
useful for building a lead list.

### 1. One-time setup

1. Go to <https://console.cloud.google.com>, create a project.
2. Enable **Places API** and **Geocoding API** for the project.
3. Under **Credentials**, create an API key.
4. **Restrict the key**: limit it to the Places API and Geocoding API,
   and add an IP or referrer restriction so it can't be abused if leaked.
5. Add a billing account. Google gives $200/month free — you won't be
   charged under that unless you scan huge areas.

### 2. Run it

```bash
export GOOGLE_MAPS_API_KEY="your-key-here"

# Barbershops within 3 km of Martensville
python3 tools/find_businesses_without_websites.py \
    --address "Martensville, SK" \
    --radius 3000 \
    --keyword "barber shop" \
    --out leads.csv
```

Options:

| Flag         | Meaning                                                              |
| ------------ | -------------------------------------------------------------------- |
| `--address`  | Center point as an address (script geocodes it). Or use `--lat/--lng`. |
| `--lat/--lng`| Center as coordinates instead of an address.                         |
| `--radius`   | Search radius in meters (max 50 000).                                |
| `--keyword`  | What to search for — `"barber shop"`, `"hair salon"`, `"cafe"`, etc. |
| `--out`      | Output CSV path (default `leads.csv`).                               |
| `--all`      | Also include businesses that DO have a website (adds them to CSV).   |

### 3. Output

CSV columns: `name, address, phone, website, has_website, rating,
review_count, type, maps_url`.

By default only rows with no website are exported. Open in Excel/Sheets,
sort by rating or review count, start calling.

### Notes & limits

- Google returns up to **60 results per search** (3 pages of 20). For a
  large area, run several smaller searches with different center points
  and dedupe by name+address.
- `has_website = no` means the business hasn't listed a site on Google —
  they may still have a Facebook page or an unlisted site. Worth checking
  before you pitch.
- The API key never touches the repo — it lives in your env only. Don't
  commit the generated `leads.csv` either (added to `.gitignore`).
