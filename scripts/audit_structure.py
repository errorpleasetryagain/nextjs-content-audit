"""
audit_structure.py — Article quality scorer for Next.js MDX content sites

Scores every MDX article out of 10 based on structural quality signals:
presence of key components, internal linking, SEO metadata completeness,
and author attribution.

Outputs worst-scoring articles first so you know where to focus.

Usage:
    python3 scripts/audit_structure.py
    SITE_REPO=/path/to/project python3 scripts/audit_structure.py

Output:
    Prints a summary table to stdout.
    Writes a full report to /tmp/structure_audit.md
"""

import os
import re
import sys
from typing import Optional


# ── Configuration ─────────────────────────────────────────────────────────────

REPO = os.environ.get("SITE_REPO", os.getcwd())

CONTENT_SUBDIRS = ["blog", "articles", "guides"]

# Report output path
REPORT_PATH = "/tmp/structure_audit.md"

# ── Component names to check for ──────────────────────────────────────────────
# Customise these to match your MDX component library.
# The checker does a simple string-contains check on the article body.

# "Author note" component — a first-person observation from the author.
# Most important humanising element. Worth 2 points.
AUTHOR_NOTE_COMPONENTS = ["<SebNote", "<AuthorNote", "<PersonalNote"]

# "Evidence/citation" component — a callout referencing a study or data source.
# Worth 2 points.
CITATION_COMPONENTS = ["<StudyCallout", "<Citation", "<ResearchNote"]

# "Commercial" component — product card, comparison table, affiliate placement.
# Worth 2 points.
COMMERCIAL_COMPONENTS = ["<ProductCard", "<ComparisonTable", "<AffiliateCard"]

# "Takeaway" component — summary of the key point in a section.
# Worth 1 point.
TAKEAWAY_COMPONENTS = ["<KeyTakeaway", "<Takeaway", "<TipBox"]

# Minimum internal links required to score the point
MIN_INTERNAL_LINKS = 3

# Maximum description length for the SEO point
MAX_DESCRIPTION_LENGTH = 155

# Author values considered valid (case-insensitive)
VALID_AUTHORS = ["seb", "sebastian", "author"]  # edit to match your pen name(s)

# Route prefixes that count as internal links
# e.g. /blog/, /guides/, /articles/
INTERNAL_LINK_PREFIXES = ["blog", "guides", "articles", "lists"]


# ── Scoring ───────────────────────────────────────────────────────────────────


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and return (fm_dict, body)."""
    fm = {}
    body = raw

    if not raw.startswith("---"):
        return fm, body

    end = raw.find("---", 3)
    if end < 0:
        return fm, body

    fm_text = raw[3:end]
    body = raw[end + 3 :]

    # Simple key: value parser (avoids yaml dependency)
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip("\"'")

    return fm, body


def has_any_component(body: str, components: list) -> bool:
    return any(c in body for c in components)


def count_internal_links(body: str) -> int:
    pattern = r"\(/({})/[^)]+\)".format("|".join(INTERNAL_LINK_PREFIXES))
    return len(re.findall(pattern, body))


def score_article(fname: str, subdir: str, raw: str) -> dict:
    fm, body = parse_frontmatter(raw)

    score = 0
    issues = []

    # Author note (2 pts)
    if has_any_component(body, AUTHOR_NOTE_COMPONENTS):
        score += 2
    else:
        issues.append(f"NO author note component ({'/'.join(AUTHOR_NOTE_COMPONENTS[:2])})")

    # Citation / evidence (2 pts)
    if has_any_component(body, CITATION_COMPONENTS):
        score += 2
    else:
        issues.append(f"NO citation component ({'/'.join(CITATION_COMPONENTS[:2])})")

    # Commercial component (2 pts)
    if has_any_component(body, COMMERCIAL_COMPONENTS):
        score += 2
    else:
        issues.append(f"NO commercial component ({'/'.join(COMMERCIAL_COMPONENTS[:2])})")

    # Takeaway (1 pt)
    if has_any_component(body, TAKEAWAY_COMPONENTS):
        score += 1
    else:
        issues.append(f"no takeaway component ({TAKEAWAY_COMPONENTS[0]})")

    # Internal links (1 pt)
    link_count = count_internal_links(body)
    if link_count >= MIN_INTERNAL_LINKS:
        score += 1
    else:
        issues.append(f"only {link_count} internal links (need {MIN_INTERNAL_LINKS}+)")

    # Description length (1 pt)
    desc = fm.get("description", "")
    if desc and len(desc) <= MAX_DESCRIPTION_LENGTH:
        score += 1
    elif len(desc) > MAX_DESCRIPTION_LENGTH:
        issues.append(f"description {len(desc)} chars (over {MAX_DESCRIPTION_LENGTH})")
    else:
        issues.append("missing description")

    # Author (1 pt)
    author = fm.get("author", "").lower()
    if author in [v.lower() for v in VALID_AUTHORS]:
        score += 1
    else:
        issues.append(f'author="{fm.get("author", "")}" (should be one of {VALID_AUTHORS})')

    return {
        "score": score,
        "file": f"{subdir}/{fname}",
        "slug": fname.replace(".mdx", ""),
        "title": fm.get("title", "(no title)"),
        "issues": issues,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    if not os.path.exists(REPO):
        print(f"ERROR: SITE_REPO path does not exist: {REPO}", file=sys.stderr)
        sys.exit(1)

    print(f"Auditing structure: {REPO}")
    results = []

    for subdir in CONTENT_SUBDIRS:
        content_dir = os.path.join(REPO, "content", subdir)
        if not os.path.exists(content_dir):
            continue

        for fname in sorted(os.listdir(content_dir)):
            if not fname.endswith(".mdx"):
                continue
            fpath = os.path.join(content_dir, fname)
            with open(fpath, encoding="utf-8") as fp:
                raw = fp.read()
            results.append(score_article(fname, subdir, raw))

    if not results:
        print("No MDX articles found. Check CONTENT_SUBDIRS configuration.")
        sys.exit(0)

    results.sort(key=lambda x: x["score"])

    perfect = [r for r in results if r["score"] >= 10]
    needs_work = [r for r in results if r["score"] < 7]
    ok = [r for r in results if 7 <= r["score"] < 10]

    print(f"\nTotal articles: {len(results)}")
    print(f"Perfect (10/10): {len(perfect)}")
    print(f"Good (7-9/10):   {len(ok)}")
    print(f"Needs work (<7): {len(needs_work)}")

    if needs_work:
        print(f"\nPRIORITY FIXES (worst first, showing up to 20):")
        print(f"{'Score':<8} {'File':<50} Issues")
        print("-" * 90)
        for r in needs_work[:20]:
            issues_str = " | ".join(r["issues"])
            print(f"[{r['score']}/10]  {r['file']:<50} {issues_str}")

    # Write full report
    if REPORT_PATH:
        with open(REPORT_PATH, "w", encoding="utf-8") as out:
            out.write("# Article Structure Audit\n\n")
            out.write(f"Total articles audited: {len(results)}\n\n")
            out.write(f"- Perfect (10/10): {len(perfect)}\n")
            out.write(f"- Good (7–9/10): {len(ok)}\n")
            out.write(f"- Needs work (under 7): {len(needs_work)}\n\n")

            out.write("## Priority fixes (score under 7)\n\n")
            out.write("| Score | File | Issues |\n|-------|------|--------|\n")
            for r in needs_work:
                out.write(f"| {r['score']}/10 | {r['file']} | {' | '.join(r['issues'])} |\n")

            out.write("\n## Good but not perfect (7–9/10)\n\n")
            out.write("| Score | File | Issues |\n|-------|------|--------|\n")
            for r in ok:
                out.write(f"| {r['score']}/10 | {r['file']} | {' | '.join(r['issues'])} |\n")

            out.write("\n## All articles\n\n")
            out.write("| Score | File | Issues |\n|-------|------|--------|\n")
            for r in results:
                issues_str = " | ".join(r["issues"]) if r["issues"] else "✅ PERFECT"
                out.write(f"| {r['score']}/10 | {r['file']} | {issues_str} |\n")

        print(f"\nFull report: {REPORT_PATH}")

    # Exit 1 if more than 25% of articles need work
    if len(needs_work) / len(results) > 0.25:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
