# jarvis-rss-digest-site

Minimal static site for Jarvis RSS digests.

## Structure

- `build.py` — copies local markdown archives from `../rss-digest/archives` and renders the static site
- `content/archives/` — copied markdown archives tracked in this repo
- `site/` — built output for GitHub Pages
- `assets/style.css` — tiny shared stylesheet

## Rebuild

```bash
cd /home/difanjia/.openclaw/rss-site-work
python3 build.py
```

After rebuilding, commit and push the updated `content/archives/` and `site/` files.
