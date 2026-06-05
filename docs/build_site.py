#!/usr/bin/env python3
"""
build_site.py — Generate the Indian Democracy HTML site from the markdown chapters.

Reads docs/markdown/NN-slug.md, converts to HTML, wraps in the shared layout
(sidebar navigation + chapter chrome) and writes to docs/site/NN-slug.html.

Run:  python3 docs/build_site.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("Install the markdown library:  python3 -m pip install --user markdown")

ROOT = Path(__file__).resolve().parent
MD_DIR = ROOT / "markdown"
SITE_DIR = ROOT / "site"

# ---------- Canonical chapter list (slug, sidebar title, sidebar group) ----------
CHAPTERS: list[tuple[str, str, str]] = [
    ("01-introduction",          "Introduction: India as a Democracy",            "Foundations"),
    ("02-constitution",          "The Constitution: Birth, Structure, Soul",      "Foundations"),
    ("03-rights-duties-dpsp",    "Rights, Duties & Directive Principles",         "Foundations"),
    ("04-federalism",            "Federalism: Union, States, UTs",                "Foundations"),
    ("05-union-executive",       "Union Executive: President, VP, PM, Cabinet",   "Union Government"),
    ("06-lok-sabha",             "Lok Sabha — The House of the People",           "Union Government"),
    ("07-rajya-sabha",           "Rajya Sabha — The Council of States",           "Union Government"),
    ("08-how-bill-becomes-law",  "How a Bill Becomes Law",                        "Union Government"),
    ("09-state-government",      "State Government: Governor, CM, MLAs",          "State Government"),
    ("10-judiciary",             "The Judiciary: Supreme Court & High Courts",    "Other Pillars"),
    ("11-eci-and-bodies",        "Election Commission & Constitutional Bodies",   "Other Pillars"),
    ("12-how-elections-work",    "How an Indian Election Actually Runs",          "Elections"),
    ("13-electoral-math",        "Electoral Systems: FPTP, STV & the Math",       "Elections"),
    ("14-local-government",      "Local Self-Government: Panchayats & Nagar Palikas", "Local Government"),
    ("15-parties-and-defection", "Political Parties & the Anti-Defection Law",    "Politics in Practice"),
    ("16-money-in-politics",     "Money in Politics: Finance, Bonds, Criminalisation", "Politics in Practice"),
    ("17-ground-execution",      "Ground-Level Campaign Execution",               "Politics in Practice"),
    ("18-recent-elections",      "Recent Elections: 2024 LS → 2026 State Cycle",  "Today"),
    ("19-glossary-references",   "Glossary, Timeline & References",               "Reference"),
]

INDEX_SLUG = "index"

# ---------- HTML layout ----------
LAYOUT = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — Indian Democracy: A Complete Guide</title>
  <meta name="description" content="{description}">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <a class="brand" href="index.html">
        <span class="brand-flag" aria-hidden="true"></span>
        <span>
          <span class="brand-title">Indian Democracy</span><br>
          <span class="brand-sub">A complete study guide</span>
        </span>
      </a>
{sidebar}
      <div class="sidebar-foot">
        Built {built_date} · Sources cited per chapter.<br>
        Anchored in M. Laxmikanth's <em>Indian Polity</em> and Shivam Shankar Singh's <em>How to Win an Indian Election</em>.
      </div>
    </aside>
    <main class="content">
      <article>
{body}
{pager}
      </article>
    </main>
  </div>
  <script src="bookmarks.js" defer></script>
</body>
</html>
"""

PAGER_HTML = """
        <nav class="pager">
          {prev}
          {next}
        </nav>"""

def build_sidebar(active_slug: str) -> str:
    """Build the sidebar nav, grouped by section, with `active` class on current page."""
    parts: list[str] = []
    current_group: str | None = None
    for slug, title, group in CHAPTERS:
        if group != current_group:
            if current_group is not None:
                parts.append("      </ol>")
            parts.append(f'      <div class="nav-section">{group}</div>')
            parts.append("      <ol>")
            current_group = group
        active = " active" if slug == active_slug else ""
        parts.append(f'        <li><a class="ch{active}" href="{slug}.html">{title}</a></li>')
    parts.append("      </ol>")
    return "\n".join(parts)

def build_pager(idx: int) -> str:
    prev_link = ""
    next_link = ""
    if idx > 0:
        slug, title, _ = CHAPTERS[idx - 1]
        prev_link = (
            f'<a href="{slug}.html"><span class="label">← Previous</span>'
            f'<strong>{title}</strong></a>'
        )
    else:
        prev_link = '<span></span>'
    if idx < len(CHAPTERS) - 1:
        slug, title, _ = CHAPTERS[idx + 1]
        next_link = (
            f'<a href="{slug}.html" style="text-align:right;">'
            f'<span class="label">Next →</span><strong>{title}</strong></a>'
        )
    else:
        next_link = '<span></span>'
    return PAGER_HTML.format(prev=prev_link, next=next_link)

def md_to_html(text: str) -> str:
    """Convert markdown body to HTML, then post-process tables to wrap in scroll containers."""
    html = markdown.markdown(
        text,
        extensions=["extra", "tables", "sane_lists", "toc", "attr_list"],
        output_format="html5",
    )
    # Wrap each <table> in a div.table-wrap for horizontal scroll on mobile.
    html = re.sub(r"(<table\b)", r'<div class="table-wrap">\1', html)
    html = re.sub(r"(</table>)", r"\1</div>", html)
    return html

def render_chapter(idx: int, slug: str, title: str) -> None:
    md_path = MD_DIR / f"{slug}.md"
    if not md_path.exists():
        print(f"  [skip] {md_path.name} not found (chapter not yet written)")
        return
    raw = md_path.read_text(encoding="utf-8")
    # Strip leading H1 if present so we can use it as title and not double-render
    body_md = re.sub(r"^# .+\n+", "", raw, count=1)
    body_html = md_to_html(body_md)
    description = first_paragraph(body_md).replace("\n", " ")[:170]
    page = LAYOUT.format(
        title=title,
        description=description,
        sidebar=build_sidebar(slug),
        body=body_html,
        pager=build_pager(idx),
        built_date="June 2026",
    )
    out = SITE_DIR / f"{slug}.html"
    out.write_text(page, encoding="utf-8")
    print(f"  [ok]   {slug}.html ({len(page):,} bytes)")

def first_paragraph(md: str) -> str:
    for block in md.split("\n\n"):
        block = block.strip()
        if block and not block.startswith(("#", "<", "-", "*", "|", ">", "1.")):
            return block
    return ""

def render_index() -> None:
    md_path = MD_DIR / "index.md"
    if not md_path.exists():
        print("  [skip] index.md not found")
        return
    raw = md_path.read_text(encoding="utf-8")
    body_md = re.sub(r"^# .+\n+", "", raw, count=1)
    body_html = md_to_html(body_md)
    page = LAYOUT.format(
        title="Home",
        description="A complete, citation-backed guide to India's democracy, government, and elections.",
        sidebar=build_sidebar("__index__"),  # nothing active
        body=body_html,
        pager="",
        built_date="June 2026",
    )
    out = SITE_DIR / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"  [ok]   index.html ({len(page):,} bytes)")

def main() -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Building site from {MD_DIR} → {SITE_DIR}")
    render_index()
    for i, (slug, title, _group) in enumerate(CHAPTERS):
        render_chapter(i, slug, title)
    print("Done.")

if __name__ == "__main__":
    main()
