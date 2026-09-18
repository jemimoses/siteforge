# SiteForge

Fill a form. Get a website. Instantly.

SiteForge lets anyone generate a fully working, styled website by filling a
simple form — site name, category, color theme, and content for whichever
sections they need (about, services, gallery, testimonials, contact). No
code, no design skills, no hosting setup. Each submission gets its own
shareable preview link at `/preview/<unique_id>`.

## Tech stack
Flask, Jinja2, SQLite, HTML/CSS

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000` in your browser.

## Deploy (free hosting)

The repo ships with a `Procfile` (gunicorn) and reads `PORT` / `SITEFORGE_SECRET_KEY` from the environment, so it deploys as-is.

> **Heads-up:** the app lives in the `siteforge/` subfolder of this repo. In Render, set **Root Directory** to `siteforge` so the build finds `requirements.txt` and the `Procfile`.

**Render** — push the repo to GitHub, then create a **Web Service** pointing at it. Build command: `pip install -r requirements.txt`, start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2`. Add `SITEFORGE_SECRET_KEY` (a long random string) under Environment.

**Railway** — create a project from the GitHub repo; it detects the Procfile automatically. Add `SITEFORGE_SECRET_KEY` under Variables.

⚠️ **Note on SQLite & uploaded images:** both live on the host's disk, so they reset on redeploy/scale on free tiers. Fine for demos; use a managed database + object storage for anything permanent.

## How it works
1. `/` — the form where a user names their site, picks a category, a color
   theme, and fills in content for the sections they want.
2. `/generate` — saves the submission to SQLite and generates a unique ID.
3. `/preview/<id>` — renders that user's content into a styled, ready page.

## Roadmap
- Custom domain support
- More section types and layout templates
- Image uploads per section
