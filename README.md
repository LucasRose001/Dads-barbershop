# Dad's Barbershop — Website

A one-page site for Dad's Barbershop, Martensville, SK.

## Files

- `index.html` — page markup
- `styles.css` — all styling (single file, no build step)
- `script.js` — mobile nav + booking form handoff
- `assets/` — drop your logo files here

## Quick customization checklist

Everything the owner should tweak lives in `index.html`. Search for these values and replace:

| Placeholder                       | Where                                   |
| --------------------------------- | --------------------------------------- |
| `(306) 555-1234`                  | Header nothing; phone/text and SMS link |
| `hello@dadsbarbershop.ca`         | Email + booking form recipient          |
| Service prices (`$30`, `$35`, …)  | `<section id="services">`               |
| Hours (Tue–Sat block)             | `<section id="hours">`                  |
| Instagram / Facebook `href="#"`   | `<div class="info-item">` (Follow row)  |
| Testimonial text                  | `<blockquote>` in the About section     |
| Exact address                     | "Address" info item in the Visit block  |

## Logo images

Save the brand marks into `assets/` with these filenames and they'll show up automatically:

- `assets/logo-primary.png` — the round black/red mark used in the header and footer
- `assets/favicon.png` — 32×32 or larger square for the browser tab

If the files aren't there yet the header text ("Dad's Barbershop") still renders — nothing breaks.

## Running locally

Any static server works. Simplest:

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploying

It's a plain static site — Netlify, Vercel, Cloudflare Pages, or GitHub Pages will all host it as-is with no build step.
