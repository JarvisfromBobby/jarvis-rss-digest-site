#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_ARCHIVES = Path("/home/difanjia/.openclaw/rss-digest/archives")
CONTENT_ARCHIVES = ROOT / "content" / "archives"
SITE_DIR = ROOT / "docs"
ASSETS_DIR = ROOT / "assets"


@dataclass
class Digest:
    title: str
    slot: str
    lookback: str
    generated: str
    item_count: int
    intro: str
    slug: str
    rel_path: str
    items: list[dict[str, str]]
    source_markdown: str


def sync_archives() -> None:
    if CONTENT_ARCHIVES.exists():
        shutil.rmtree(CONTENT_ARCHIVES)
    CONTENT_ARCHIVES.parent.mkdir(parents=True, exist_ok=True)
    if SOURCE_ARCHIVES.exists():
        shutil.copytree(SOURCE_ARCHIVES, CONTENT_ARCHIVES)
    else:
        CONTENT_ARCHIVES.mkdir(parents=True, exist_ok=True)


def md_files() -> list[Path]:
    return sorted([p for p in CONTENT_ARCHIVES.rglob('*.md') if p.name != 'latest.md'], reverse=True)


def parse_digest(path: Path) -> Digest:
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    title = lines[0].replace('# ', '').strip() if lines else path.stem
    slot = re.search(r"- Slot: `([^`]+)`", text).group(1)
    lookback = re.search(r"- Lookback: `([^`]+)`", text).group(1)
    generated = re.search(r"- Generated: `([^`]+)`", text).group(1)
    item_count = int(re.search(r"- Item count: `([^`]+)`", text).group(1))
    intro_match = re.search(r"- Item count: `[^`]+`\n\n(.+?)\n\n## 1\.", text, re.S)
    intro = intro_match.group(1).strip() if intro_match else ''
    sections = re.split(r"\n## ", text)
    items: list[dict[str, str]] = []
    for section in sections[1:]:
        sec_lines = section.strip().splitlines()
        if not sec_lines:
            continue
        heading = sec_lines[0].strip()
        body = '\n'.join(sec_lines[1:])

        def field(name: str) -> str:
            m = re.search(rf"- {re.escape(name)}: (.+)", body)
            return m.group(1).strip() if m else ''

        items.append({
            'heading': heading,
            'category': field('Category'),
            'feed': field('Feed'),
            'published': field('Published'),
            'link': field('Link'),
            'summary': field('Summary'),
        })
    rel = path.relative_to(CONTENT_ARCHIVES)
    slug = path.with_suffix('.html').name
    return Digest(title, slot, lookback, generated, item_count, intro, slug, rel.as_posix(), items, text)


def page(title: str, body: str, active: str = '') -> str:
    nav = f"""
    <nav class=\"nav\">
      <a href=\"/\" {'class="active"' if active == 'home' else ''}>Home</a>
      <a href=\"/archives/\" {'class="active"' if active == 'archives' else ''}>Archives</a>
      <a href=\"https://github.com/JarvisfromBobby/jarvis-rss-digest-site\">GitHub</a>
    </nav>
    """
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <meta name=\"description\" content=\"A lightweight, readable archive for Jarvis RSS digests.\">
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap\" rel=\"stylesheet\">
  <link rel=\"stylesheet\" href=\"/assets/style.css\">
</head>
<body>
  <div class=\"wrap\">
    <header class=\"hero\">
      <div class=\"hero-copy\">
        <p class=\"eyebrow\">Jarvis RSS Digest</p>
        <h1>{html.escape(title)}</h1>
        <p class=\"sub\">A lightweight, readable archive for Bobby's RSS digests — simple enough to stay fast, polished enough to actually enjoy browsing.</p>
      </div>
      {nav}
    </header>
    <main class=\"stack\">
      {body}
    </main>
    <p class=\"footer-note\">Static HTML, local markdown, zero framework drama.</p>
  </div>
</body>
</html>
"""


def render_digest(d: Digest) -> str:
    cards = []
    for item in d.items:
        tags = ''.join(
            f"<span class=\"pill\">{html.escape(value)}</span>"
            for value in [item['category'], item['feed'], item['published']]
            if value
        )
        summary = f"<p>{html.escape(item['summary'])}</p>" if item['summary'] else ''
        link = (
            f"<p><a class=\"source-link\" href=\"{html.escape(item['link'])}\">Open source <span aria-hidden=\"true\">↗</span></a></p>"
            if item['link'] else ''
        )
        cards.append(f"""
        <article class=\"card item\">
          <h3>{html.escape(item['heading'])}</h3>
          <div class=\"meta-line\">{tags}</div>
          {summary}
          {link}
        </article>
        """)

    intro = f"<p class=\"digest-intro\">{html.escape(d.intro)}</p>" if d.intro else ''
    body = f"""
    <section class=\"card digest-meta\">
      <div class=\"kicker-row\">
        <div>
          <p class=\"eyebrow\">Digest overview</p>
          <h2>{html.escape(d.title)}</h2>
          {intro}
        </div>
        <a class=\"cta-link\" href=\"/archives/\">Back to archive</a>
      </div>
      <div class=\"stats\">
        <div class=\"stat\"><span class=\"stat-label\">Generated</span><span class=\"stat-value\">{html.escape(d.generated)}</span></div>
        <div class=\"stat\"><span class=\"stat-label\">Slot</span><span class=\"stat-value\">{html.escape(d.slot)}</span></div>
        <div class=\"stat\"><span class=\"stat-label\">Lookback</span><span class=\"stat-value\">{html.escape(d.lookback)}</span></div>
        <div class=\"stat\"><span class=\"stat-label\">Items</span><span class=\"stat-value\">{d.item_count}</span></div>
      </div>
      <p class=\"archive-note\">Source file: <code>{html.escape(d.rel_path)}</code></p>
    </section>
    <section class=\"list\">{''.join(cards)}</section>
    """
    return page(d.title, body, active='archives')


def render_home(current: Digest | None, digests: list[Digest]) -> str:
    latest = ''
    if current:
        items = ''.join(
            f"<li><a href=\"{html.escape(item['link'])}\">{html.escape(item['heading'])}</a> <span>{html.escape(item['feed'])}</span></li>"
            if item['link'] else f"<li>{html.escape(item['heading'])}</li>"
            for item in current.items[:8]
        )
        intro = f"<p class=\"digest-intro\">{html.escape(current.intro)}</p>" if current.intro else ''
        latest = f"""
        <section class=\"card latest\">
          <div class=\"section-head\">
            <div>
              <p class=\"eyebrow\">Latest issue</p>
              <h2>Latest digest</h2>
            </div>
            <a href=\"/archives/{html.escape(current.slug)}\">Open full digest</a>
          </div>
          <div class=\"meta-line\">
            <span class=\"pill\">{html.escape(current.generated)}</span>
            <span class=\"pill\">{html.escape(current.slot)}</span>
            <span class=\"pill\">{current.item_count} items</span>
          </div>
          {intro}
          <ul class=\"latest-list\">{items}</ul>
        </section>
        """
    archive_items = ''.join(
        f"<li><a href=\"/archives/{html.escape(d.slug)}\">{html.escape(d.generated)}</a> <span>{html.escape(d.slot)} · {d.item_count} items</span></li>"
        for d in digests[:12]
    )
    body = f"""
    {latest}
    <section class=\"grid\">
      <article class=\"card\">
        <div class=\"section-head\">
          <div>
            <p class=\"eyebrow\">Browse</p>
            <h2>Archive</h2>
          </div>
          <a href=\"/archives/\">See all digests</a>
        </div>
        <p>Each issue is generated from local markdown under <code>rss-digest/archives/</code>, then published as a lightweight static archive.</p>
        <ul class=\"archive-list\">{archive_items}</ul>
      </article>
      <article class=\"card\">
        <p class=\"eyebrow\">About</p>
        <h2>How this works</h2>
        <p>The RSS workflow stores every sent digest as markdown. This repo syncs those files, rebuilds the site, and deploys to GitHub Pages.</p>
        <p>Fast to load, easy to maintain, pleasant to read.</p>
      </article>
    </section>
    """
    return page('Jarvis RSS Digest', body, active='home')


def render_archives_index(digests: list[Digest]) -> str:
    items = ''.join(
        f"<li><a href=\"/archives/{html.escape(d.slug)}\">{html.escape(d.generated)}</a><span>{html.escape(d.slot)} · {d.item_count} items</span></li>"
        for d in digests
    )
    body = f"""
    <section class=\"card\">
      <div class=\"section-head\">
        <div>
          <p class=\"eyebrow\">Archive</p>
          <h2>All archived digests</h2>
        </div>
      </div>
      <p>Every published issue, in reverse chronological order.</p>
      <ul class=\"archive-list\">{items}</ul>
    </section>
    """
    return page('Digest Archives', body, active='archives')


def build() -> None:
    sync_archives()
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    (SITE_DIR / 'archives').mkdir(parents=True, exist_ok=True)
    (SITE_DIR / 'assets').mkdir(parents=True, exist_ok=True)
    shutil.copy2(ASSETS_DIR / 'style.css', SITE_DIR / 'assets' / 'style.css')

    digests = [parse_digest(p) for p in md_files()]
    current = digests[0] if digests else None

    (SITE_DIR / 'index.html').write_text(render_home(current, digests), encoding='utf-8')
    (SITE_DIR / 'archives' / 'index.html').write_text(render_archives_index(digests), encoding='utf-8')
    for digest in digests:
        (SITE_DIR / 'archives' / digest.slug).write_text(render_digest(digest), encoding='utf-8')


if __name__ == '__main__':
    build()
