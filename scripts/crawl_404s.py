"""
crawl_404s.py — Broken internal link scanner for Next.js MDX content sites

Scans all MDX files in content/ directories, extracts every internal link,
and checks it against the set of valid routes derived from your content files.

Usage:
    python3 scripts/crawl_404s.py
    SITE_REPO=/path/to/project python3 scripts/crawl_404s.py

Output:
    Prints a summary and list of broken links.
    Writes a full report to /tmp/404_report.md
"""

import os
import re
import sys


# ── Configuration ────────────────────────────────────────────────────────────

# Set SITE_REPO env var or edit this default path
REPO = os.environ.get("SITE_REPO", os.getcwd())

# Subdirectories under content/ that contain MDX articles
# Edit this to match your project structure
CONTENT_SUBDIRS = ["blog", "articles", "guides", "lists"]

# Static pages that always exist (not derived from content files)
# Add any static pages your site has
STATIC_PAGES = [
    "/",
    "/blog",
    "/articles",
    "/guides",
    "/lists",
    "/about",
    "/contact",
    "/privacy",
    "/terms",
]

# Route mapping: if you serve content/articles/ at /blog/, add it here
ROUTE_ALIASES = {
    "articles": "blog",  # content/articles/foo.mdx → /blog/foo
}

# Report output path (set to None to skip writing a file)
REPORT_PATH = "/tmp/404_report.md"


# ── Main logic ────────────────────────────────────────────────────────────────


def build_valid_slugs(repo: str) -> set:
    """Build the set of all valid route paths from content files."""
    valid = set(STATIC_PAGES)

    for subdir in CONTENT_SUBDIRS:
        content_dir = os.path.join(repo, "content", subdir)
        if not os.path.exists(content_dir):
            continue

        route_prefix = ROUTE_ALIASES.get(subdir, subdir)

        for fname in os.listdir(content_dir):
            if fname.endswith(".mdx"):
                slug = fname.replace(".mdx", "")
                valid.add(f"/{route_prefix}/{slug}")

    return valid


def extract_links(content: str) -> list:
    """Extract all internal links from MDX content."""
    links = []
    # Markdown links: [text](/path)
    links += re.findall(r"\]\((/[^)#?]+)", content)
    # JSX href props: href="/path" or href='/path'
    links += re.findall(r'href=["\'](/[^"\'#?]+)["\']', content)
    return links


def scan_content(repo: str, valid_slugs: set) -> tuple:
    """Scan all MDX files for broken links."""
    broken = []
    total_links = 0

    for subdir in CONTENT_SUBDIRS:
        content_dir = os.path.join(repo, "content", subdir)
        if not os.path.exists(content_dir):
            continue

        for fname in os.listdir(content_dir):
            if not fname.endswith(".mdx"):
                continue

            fpath = os.path.join(content_dir, fname)
            with open(fpath, encoding="utf-8") as fp:
                content = fp.read()

            links = extract_links(content)

            for link in links:
                total_links += 1
                # Normalise: strip trailing slash, query string, fragment
                clean = link.split("?")[0].split("#")[0].rstrip("/")
                if not clean:
                    continue
                # Skip API routes — these are valid but not content pages
                if clean.startswith("/api/"):
                    continue
                if clean not in valid_slugs:
                    broken.append(
                        {
                            "file": f"content/{subdir}/{fname}",
                            "link": link,
                            "clean": clean,
                        }
                    )

    return broken, total_links


def write_report(broken: list, total_links: int, path: str):
    """Write a Markdown report of broken links."""
    with open(path, "w", encoding="utf-8") as out:
        out.write("# 404 Audit Report\n\n")
        out.write(f"Total links scanned: {total_links}\n")
        out.write(f"Broken links found: {len(broken)}\n\n")

        if broken:
            out.write("## Broken links\n\n")
            out.write("| File | Link | Cleaned path |\n")
            out.write("|------|------|------|\n")
            seen = set()
            for item in sorted(broken, key=lambda x: x["file"]):
                key = (item["file"], item["clean"])
                if key in seen:
                    continue
                seen.add(key)
                out.write(f"| {item['file']} | `{item['link']}` | `{item['clean']}` |\n")
        else:
            out.write("## ✅ No broken internal links found\n")


def main():
    if not os.path.exists(REPO):
        print(f"ERROR: SITE_REPO path does not exist: {REPO}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning: {REPO}")

    valid_slugs = build_valid_slugs(REPO)
    broken, total_links = scan_content(REPO, valid_slugs)

    # Deduplicate
    seen = set()
    unique_broken = []
    for item in broken:
        key = (item["file"], item["clean"])
        if key not in seen:
            seen.add(key)
            unique_broken.append(item)

    print(f"Links scanned: {total_links}")
    print(f"Broken links: {len(unique_broken)}")

    if unique_broken:
        print("\nBROKEN LINKS:")
        for item in sorted(unique_broken, key=lambda x: x["file"]):
            print(f"  {item['file']} → {item['link']}")
        print()

        if REPORT_PATH:
            write_report(unique_broken, total_links, REPORT_PATH)
            print(f"Full report: {REPORT_PATH}")

        sys.exit(1)
    else:
        print("✅ No broken internal links")
        sys.exit(0)


if __name__ == "__main__":
    main()
