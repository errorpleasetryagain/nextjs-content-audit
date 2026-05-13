"""
content_quality.py — Content writing quality checks for MDX articles

Checks for:
- American spellings in UK-English sites
- Banned AI-generated phrases ("In conclusion", "Delve into", etc.)
- Em dash / en dash usage (where your style guide prohibits them)

These are soft checks — any failures are LOW severity, not build-breaking.
But they compound over hundreds of articles and slowly erode your brand voice.

Usage:
    python3 scripts/content_quality.py
    SITE_REPO=/path/to/project python3 scripts/content_quality.py

Configuration:
    - Set CHECK_UK_ENGLISH=false to skip American spelling check
    - Set CHECK_BANNED_PHRASES=false to skip banned phrases check
    - Set CHECK_EM_DASHES=false to skip em dash check
    - Edit AMERICAN_SPELLINGS, BANNED_PHRASES lists below to match your style guide
"""

import os
import re
import sys


# ── Configuration ─────────────────────────────────────────────────────────────

REPO = os.environ.get("SITE_REPO", os.getcwd())
CONTENT_SUBDIRS = ["blog", "articles", "guides"]

CHECK_UK_ENGLISH = os.environ.get("CHECK_UK_ENGLISH", "true").lower() != "false"
CHECK_BANNED_PHRASES = os.environ.get("CHECK_BANNED_PHRASES", "true").lower() != "false"
CHECK_EM_DASHES = os.environ.get("CHECK_EM_DASHES", "true").lower() != "false"

# American spellings → UK equivalents
# Extend this list to match your needs
AMERICAN_SPELLINGS = [
    r"\boptimize\b",
    r"\boptimized\b",
    r"\boptimizing\b",
    r"\boptimization\b",
    r"\banalyze\b",
    r"\banalyzed\b",
    r"\bcolor\b",
    r"\bfavor\b",
    r"\bfavorite\b",
    r"\bbehavior\b",
    r"\bcenter\b",
    r"\bfiber\b",
    r"\borganize\b",
    r"\brecognize\b",
    r"\bsummarize\b",
    r"\bspecialize\b",
    r"\bneutralize\b",
    r"\bmonitor\b",  # fine in UK too, but listed as example
]

# Phrases that signal AI-generated content or weak writing
# Customise for your brand voice
BANNED_PHRASES = [
    r"in conclusion",
    r"to conclude",
    r"in summary",
    r"to summarise",
    r"to summarize",
    r"it is worth noting",
    r"it's worth noting",
    r"delve into",
    r"comprehensive guide",
    r"game.?changing",
    r"harness the power",
    r"navigate the complexities",
    r"at the end of the day",
    r"this article will",
    r"in this article",
    r"furthermore,",
    r"moreover,",
    r"additionally,",
    r"ensuring that",
    r"\bleverage\b",  # as a verb
    r"\brobust\b",   # unless discussing actual robustness
]


# ── Main ──────────────────────────────────────────────────────────────────────


def check_file(fpath: str, label: str) -> dict:
    with open(fpath, encoding="utf-8") as fp:
        content = fp.read()

    # Skip frontmatter for content checks
    body = content
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            body = content[end + 3 :]

    results = {
        "label": label,
        "american": [],
        "banned": [],
        "em_dashes": 0,
    }

    if CHECK_UK_ENGLISH:
        for pattern in AMERICAN_SPELLINGS:
            matches = re.findall(pattern, body, re.IGNORECASE)
            if matches:
                results["american"].extend(matches)

    if CHECK_BANNED_PHRASES:
        for pattern in BANNED_PHRASES:
            if re.search(pattern, body, re.IGNORECASE):
                phrase = pattern.replace(r"\b", "").replace("?", "")
                results["banned"].append(phrase)

    if CHECK_EM_DASHES:
        # en dash (–) and em dash (—) surrounded by spaces
        results["em_dashes"] = len(re.findall(r" [–—] ", body))

    return results


def main():
    if not os.path.exists(REPO):
        print(f"ERROR: SITE_REPO path does not exist: {REPO}", file=sys.stderr)
        sys.exit(1)

    print(f"Content quality check: {REPO}")

    all_results = []

    for subdir in CONTENT_SUBDIRS:
        content_dir = os.path.join(REPO, "content", subdir)
        if not os.path.exists(content_dir):
            continue

        for fname in os.listdir(content_dir):
            if not fname.endswith(".mdx"):
                continue
            fpath = os.path.join(content_dir, fname)
            label = f"{subdir}/{fname}"
            all_results.append(check_file(fpath, label))

    # Aggregate
    total_american = sum(len(r["american"]) for r in all_results)
    files_with_banned = [r for r in all_results if r["banned"]]
    total_em = sum(r["em_dashes"] for r in all_results)

    print(f"\nFiles scanned:            {len(all_results)}")
    if CHECK_UK_ENGLISH:
        print(f"American spelling hits:   {total_american}")
    if CHECK_BANNED_PHRASES:
        print(f"Files with banned phrases:{len(files_with_banned)}")
    if CHECK_EM_DASHES:
        print(f"Em/en dash occurrences:   {total_em}")

    has_issues = total_american > 0 or files_with_banned or total_em > 0

    if files_with_banned:
        print("\n── FILES WITH BANNED PHRASES ──")
        for r in files_with_banned[:15]:
            print(f"  {r['label']}: {', '.join(r['banned'])}")

    if total_american > 0 and CHECK_UK_ENGLISH:
        files_with_american = [r for r in all_results if r["american"]]
        print(f"\n── AMERICAN SPELLINGS (first 10 files) ──")
        for r in files_with_american[:10]:
            print(f"  {r['label']}: {', '.join(set(r['american']))}")

    if total_em > 0 and CHECK_EM_DASHES:
        files_with_em = [r for r in all_results if r["em_dashes"] > 0]
        print(f"\n── EM/EN DASHES (first 10 files) ──")
        for r in files_with_em[:10]:
            print(f"  {r['label']}: {r['em_dashes']} occurrence(s)")

    if not has_issues:
        print("\n✅ All content quality checks passed")

    # These are LOW severity — don't exit 1, just report
    sys.exit(0)


if __name__ == "__main__":
    main()
