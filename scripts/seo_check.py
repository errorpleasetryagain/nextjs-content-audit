"""
seo_check.py — Title and meta description length checker

The most common cause of page-1 rankings with zero clicks:
titles over 60 chars get truncated in SERPs, losing CTR.

This script scans all MDX frontmatter for:
- Titles over 60 characters (truncated in search results)
- Descriptions over 155 characters (truncated in search results)
- Missing descriptions
- Descriptions ending without punctuation (can look truncated)

Usage:
    python3 scripts/seo_check.py
    SITE_REPO=/path/to/project python3 scripts/seo_check.py
"""

import os
import re
import sys


# ── Configuration ─────────────────────────────────────────────────────────────

REPO = os.environ.get("SITE_REPO", os.getcwd())
CONTENT_SUBDIRS = ["blog", "articles", "guides"]

MAX_TITLE_LENGTH = 60
MAX_DESC_LENGTH = 155

REPORT_PATH = "/tmp/seo_report.md"


# ── Main ──────────────────────────────────────────────────────────────────────


def extract_frontmatter_field(content: str, field: str) -> str:
    """Extract a single frontmatter field value."""
    pattern = rf"^{field}:\s*[\"']?(.+?)[\"']?\s*$"
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        return ""
    return m.group(1).strip().strip("\"'")


def main():
    if not os.path.exists(REPO):
        print(f"ERROR: SITE_REPO path does not exist: {REPO}", file=sys.stderr)
        sys.exit(1)

    print(f"SEO check: {REPO}")

    titles_over = []
    descs_over = []
    descs_missing = []
    descs_truncated = []

    for subdir in CONTENT_SUBDIRS:
        content_dir = os.path.join(REPO, "content", subdir)
        if not os.path.exists(content_dir):
            continue

        for fname in os.listdir(content_dir):
            if not fname.endswith(".mdx"):
                continue

            fpath = os.path.join(content_dir, fname)
            with open(fpath, encoding="utf-8") as fp:
                content = fp.read()

            label = f"{subdir}/{fname}"

            title = extract_frontmatter_field(content, "title")
            if title and len(title) > MAX_TITLE_LENGTH:
                titles_over.append((len(title), label, title))

            desc = extract_frontmatter_field(content, "description")
            if not desc:
                descs_missing.append(label)
            elif len(desc) > MAX_DESC_LENGTH:
                descs_over.append((len(desc), label, desc))
            elif desc and desc[-1] not in ".!?)":
                descs_truncated.append((len(desc), label, desc))

    # Sort worst first
    titles_over.sort(reverse=True)
    descs_over.sort(reverse=True)

    # Print summary
    has_issues = titles_over or descs_over or descs_missing

    print(f"\nTitles over {MAX_TITLE_LENGTH} chars:  {len(titles_over)}")
    print(f"Descriptions over {MAX_DESC_LENGTH} chars: {len(descs_over)}")
    print(f"Missing descriptions:         {len(descs_missing)}")
    print(f"Truncated descriptions:       {len(descs_truncated)}")

    if titles_over:
        print(f"\n── TITLES OVER {MAX_TITLE_LENGTH} CHARS (worst first) ──")
        for length, label, title in titles_over[:20]:
            print(f"  {length}ch | {label}")
            print(f"         {title}")

    if descs_over:
        print(f"\n── DESCRIPTIONS OVER {MAX_DESC_LENGTH} CHARS (worst first) ──")
        for length, label, desc in descs_over[:15]:
            print(f"  {length}ch | {label}")
            print(f"         {desc[:100]}...")

    if descs_missing[:10]:
        print("\n── MISSING DESCRIPTION (first 10) ──")
        for label in descs_missing[:10]:
            print(f"  {label}")

    # Write full report
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as out:
            out.write("# SEO Check Report\n\n")
            out.write(f"- Titles over {MAX_TITLE_LENGTH} chars: **{len(titles_over)}**\n")
            out.write(f"- Descriptions over {MAX_DESC_LENGTH} chars: **{len(descs_over)}**\n")
            out.write(f"- Missing descriptions: **{len(descs_missing)}**\n")
            out.write(f"- Truncated descriptions (no end punct): **{len(descs_truncated)}**\n\n")

            if titles_over:
                out.write(f"## Titles over {MAX_TITLE_LENGTH} chars\n\n")
                out.write("| Chars | File | Title |\n|-------|------|-------|\n")
                for length, label, title in titles_over:
                    out.write(f"| {length} | {label} | {title} |\n")
                out.write("\n")

            if descs_over:
                out.write(f"## Descriptions over {MAX_DESC_LENGTH} chars\n\n")
                out.write("| Chars | File | Description (truncated) |\n|-------|------|---------|\n")
                for length, label, desc in descs_over:
                    out.write(f"| {length} | {label} | {desc[:80]}... |\n")
                out.write("\n")

            if descs_missing:
                out.write("## Missing descriptions\n\n")
                for label in descs_missing:
                    out.write(f"- {label}\n")

        print(f"\nFull report: {REPORT_PATH}")

    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
