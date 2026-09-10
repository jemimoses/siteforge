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

## How it works
1. `/` — the form where a user names their site, picks a category, a color
   theme, and fills in content for the sections they want.
2. `/generate` — saves the submission to SQLite and generates a unique ID.
3. `/preview/<id>` — renders that user's content into a styled, ready page.

## Roadmap
- Custom domain support
- More section types and layout templates
- Image uploads per section
