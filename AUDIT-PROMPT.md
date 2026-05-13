# Next.js Content Site — Full Audit
#
# Run with Claude Code:
#   claudex "$(cat AUDIT-PROMPT.md)"
#
# Override project path:
#   SITE_REPO=/path/to/project claudex "$(cat AUDIT-PROMPT.md)"
#
# 16 checks. Read-only. Compiles a single Markdown report.
# To auto-fix after reviewing: pass the report to your fix workflow.

---

## Setup

```bash
REPO="${SITE_REPO:-$(pwd)}"
cd "$REPO"
SITE_NAME=$(basename "$REPO")
REPORT_DATE=$(date +%Y-%m-%d)
REPORT_FILE="$(pwd)/AUDIT-REPORT-${SITE_NAME}-${REPORT_DATE}.md"
echo "Auditing: $SITE_NAME"
echo "Report: $REPORT_FILE"
```

---

## CHECK 1 — TypeScript build health

```bash
npx tsc --noEmit 2>&1 | grep -v "node_modules" | head -40
echo "TSC EXIT: $?"
```

**Pass:** zero errors
**Fail:** any TypeScript error = CRITICAL

---

## CHECK 2 — CSS design token integrity

```bash
# Check core CSS variables exist
grep -n "bg-page\|bg-card\|accent\|overflow-x" app/globals.css 2>/dev/null || \
  grep -n "bg-page\|bg-card\|accent\|overflow-x" styles/globals.css 2>/dev/null

# Check for rogue dark/white backgrounds in components
echo "--- Dark backgrounds in non-hero/footer components ---"
grep -rn "bg-black\|bg-zinc-950\|bg-gray-950\|#111111\|#0a0a0a" \
  app/ components/ --include="*.tsx" 2>/dev/null | \
  grep -v "footer\|Footer\|hero\|Hero\|node_modules" | head -10

echo "--- White card backgrounds (should use your brand card colour) ---"
grep -rn "bg-white" components/ --include="*.tsx" 2>/dev/null | \
  grep -v "node_modules\|button\|Button\|input\|Input" | head -10
```

**Pass:** CSS variables defined, no rogue dark/white backgrounds
**Fail:** missing CSS var = HIGH | dark backgrounds = HIGH | white cards = MEDIUM

---

## CHECK 3 — Routing consistency

```bash
# Find any stale route references (customise these for your routing)
# Example: if you renamed /articles/ to /blog/
grep -rn '"/articles/' app/ components/ content/ \
  --include="*.tsx" --include="*.mdx" 2>/dev/null | \
  grep -v "node_modules\|redirect\|rewrite" | head -10
```

**Pass:** no stale route references
**Fail:** stale routes = MEDIUM

---

## CHECK 4 — Broken internal links

```python
python3 - <<'PYEOF'
import os, re, sys

repo = os.environ.get('SITE_REPO', os.getcwd())
CONTENT_SUBDIRS = ['blog', 'articles', 'guides', 'lists']
ROUTE_ALIASES = {'articles': 'blog'}
STATIC_PAGES = ['/', '/blog', '/articles', '/guides', '/lists',
                '/about', '/contact', '/privacy', '/terms']

valid = set(STATIC_PAGES)
for sub in CONTENT_SUBDIRS:
    d = os.path.join(repo, 'content', sub)
    if not os.path.exists(d): continue
    prefix = ROUTE_ALIASES.get(sub, sub)
    for f in os.listdir(d):
        if f.endswith('.mdx'):
            valid.add(f'/{prefix}/{f[:-4]}')

broken = []
total = 0
for sub in CONTENT_SUBDIRS:
    d = os.path.join(repo, 'content', sub)
    if not os.path.exists(d): continue
    for f in os.listdir(d):
        if not f.endswith('.mdx'): continue
        with open(os.path.join(d, f)) as fp: content = fp.read()
        links = re.findall(r'\]\((/[^)#?]+)', content)
        links += re.findall(r'href=["\'](/[^"\'#?]+)["\']', content)
        for link in links:
            total += 1
            clean = link.split('?')[0].split('#')[0].rstrip('/')
            if clean and clean not in valid and not clean.startswith('/api/'):
                broken.append((f'content/{sub}/{f}', link))

print(f'Links scanned: {total}')
print(f'Broken: {len(broken)}')
if broken:
    for file, link in sorted(set(broken)):
        print(f'  {file} → {link}')
else:
    print('✅ No broken internal links')
PYEOF
```

**Pass:** 0 broken links
**Fail:** any broken link = HIGH

---

## CHECK 5 — Article structure quality

```python
python3 - <<'PYEOF'
import os, re

repo = os.environ.get('SITE_REPO', os.getcwd())
CONTENT_SUBDIRS = ['blog', 'articles', 'guides']

# Customise these component names to match your MDX library
AUTHOR_NOTE = ['<SebNote', '<AuthorNote']
CITATION = ['<StudyCallout', '<Citation']
COMMERCIAL = ['<ProductCard', '<ComparisonTable']
TAKEAWAY = ['<KeyTakeaway', '<Takeaway']

results = []
for sub in CONTENT_SUBDIRS:
    d = os.path.join(repo, 'content', sub)
    if not os.path.exists(d): continue
    for f in sorted(os.listdir(d)):
        if not f.endswith('.mdx'): continue
        with open(os.path.join(d, f)) as fp: raw = fp.read()
        fm, body = {}, raw
        if raw.startswith('---'):
            end = raw.find('---', 3)
            if end > 0:
                for line in raw[3:end].splitlines():
                    if ':' in line:
                        k, _, v = line.partition(':')
                        fm[k.strip()] = v.strip().strip("\"'")
                body = raw[end+3:]
        score, issues = 0, []
        if any(c in body for c in AUTHOR_NOTE): score += 2
        else: issues.append('NO author note component')
        if any(c in body for c in CITATION): score += 2
        else: issues.append('NO citation component')
        if any(c in body for c in COMMERCIAL): score += 2
        else: issues.append('NO commercial component')
        if any(c in body for c in TAKEAWAY): score += 1
        else: issues.append('no takeaway component')
        links = re.findall(r'\(/(blog|guides|articles|lists)/[^)]+\)', body)
        if len(links) >= 3: score += 1
        else: issues.append(f'only {len(links)} internal links (need 3+)')
        desc = fm.get('description', '')
        if desc and len(desc) <= 155: score += 1
        elif len(desc) > 155: issues.append(f'description {len(desc)} chars (over 155)')
        else: issues.append('missing description')
        author = fm.get('author', '').lower()
        if author: score += 1
        else: issues.append('no author field')
        results.append({'score': score, 'file': f'{sub}/{f}', 'issues': issues})

results.sort(key=lambda x: x['score'])
needs_work = [r for r in results if r['score'] < 7]
perfect = [r for r in results if r['score'] >= 10]

print(f'Total: {len(results)} | Perfect: {len(perfect)} | Needs work: {len(needs_work)}')
if needs_work:
    print(f'\nPriority fixes:')
    for r in needs_work[:20]:
        print(f'  [{r["score"]}/10] {r["file"]}: {" | ".join(r["issues"])}')
else:
    print('✅ All articles 7/10 or above')
PYEOF
```

**Pass:** fewer than 10% of articles under 7/10
**Fail:** >10% under 7 = MEDIUM | >25% under 7 = HIGH

---

## CHECK 6 — Meta descriptions

```python
python3 - <<'PYEOF'
import os, re

repo = os.environ.get('SITE_REPO', os.getcwd())
CONTENT_SUBDIRS = ['blog', 'articles', 'guides']
over_155, missing = [], []

for sub in CONTENT_SUBDIRS:
    d = os.path.join(repo, 'content', sub)
    if not os.path.exists(d): continue
    for f in os.listdir(d):
        if not f.endswith('.mdx'): continue
        with open(os.path.join(d, f)) as fp: content = fp.read()
        m = re.search(r'^description:\s*[">]?\s*(.+?)(?=\n\w|\Z)', content, re.MULTILINE|re.DOTALL)
        if not m:
            missing.append(f)
            continue
        desc = ' '.join(m.group(1).strip().split()).strip("\"'")
        if len(desc) > 155:
            over_155.append((len(desc), f'{sub}/{f}', desc[:80]))

print(f'Missing: {len(missing)} | Over 155 chars: {len(over_155)}')
if over_155:
    print('\nOVER 155:')
    for length, label, desc in sorted(over_155, reverse=True)[:10]:
        print(f'  {length}ch | {label}: {desc}...')
if missing[:5]:
    print(f'\nMISSING (first 5): {missing[:5]}')
if not over_155 and not missing:
    print('✅ All descriptions OK')
PYEOF
```

**Pass:** 0 over 155 chars, 0 missing
**Fail:** any over 155 = MEDIUM | any missing = HIGH

---

## CHECK 7 — Title lengths (SERP truncation)

```python
python3 - <<'PYEOF'
import os, re

repo = os.environ.get('SITE_REPO', os.getcwd())
CONTENT_SUBDIRS = ['blog', 'articles', 'guides']
over_60 = []

for sub in CONTENT_SUBDIRS:
    d = os.path.join(repo, 'content', sub)
    if not os.path.exists(d): continue
    for f in os.listdir(d):
        if not f.endswith('.mdx'): continue
        with open(os.path.join(d, f)) as fp: content = fp.read()
        m = re.search(r'^title:\s*[">]?\s*(.+?)(?=\n)', content, re.MULTILINE)
        if not m: continue
        title = m.group(1).strip().strip("\"'")
        if len(title) > 60:
            over_60.append((len(title), f'{sub}/{f}', title))

over_60.sort(reverse=True)
print(f'Titles over 60 chars: {len(over_60)}')
if over_60:
    print('\nWORST OFFENDERS:')
    for length, label, title in over_60[:15]:
        print(f'  {length}ch | {label}: {title}')
else:
    print('✅ All titles under 60 chars')
PYEOF
```

**Pass:** 0 over 60 chars
**Fail:** any over 60 = MEDIUM (these are losing clicks on page 1)

---

## CHECK 8 — UK English (if applicable)

```bash
echo "American spellings found:"
grep -rn "\boptimize\b\|\boptimized\b\|\bcolor\b\|\bfavor\b\|\bbehavior\b\|\banalyze\b" \
  content/ --include="*.mdx" 2>/dev/null | grep -v "node_modules" | wc -l
grep -rn "\boptimize\b\|\bcolor\b\|\bfavor\b\|\bbehavior\b\|\banalyze\b" \
  content/ --include="*.mdx" 2>/dev/null | head -5
```

**Pass:** 0 American spellings (skip this check if your site is not UK English)
**Fail:** any = LOW

---

## CHECK 9 — Banned AI phrases

```bash
grep -rnic "in conclusion\|it is worth noting\|delve into\|comprehensive guide\|game.changing\|harness the power\|navigate the complexities\|in summary\|this article will" \
  content/ --include="*.mdx" 2>/dev/null | grep -v ":0$" | head -15
```

**Pass:** 0 matches
**Fail:** any = LOW

---

## CHECK 10 — Em dash usage

```bash
grep -rn " — \| – " content/ --include="*.mdx" 2>/dev/null | wc -l
grep -rn " — \| – " content/ --include="*.mdx" 2>/dev/null | head -5
```

**Pass:** 0 (if your style guide prohibits em dashes — skip otherwise)
**Fail:** any = LOW

---

## CHECK 11 — Author bylines

```bash
echo "Articles without author field:"
grep -rL "^author:" content/ --include="*.mdx" 2>/dev/null | wc -l
echo "Non-standard author values:"
grep -rn "^author:" content/ --include="*.mdx" 2>/dev/null | grep -v "Seb\|Sebastian\|Author" | head -10
```

**Pass:** all articles have author field
**Fail:** missing author = MEDIUM

---

## CHECK 12 — MDX JSX safety (em dashes in prop strings)

```bash
# Em dashes inside JSX prop strings break the MDX parser silently
grep -rn 'description="[^"]*—[^"]*"\|finding="[^"]*—[^"]*"\|label="[^"]*—[^"]*"' \
  content/ --include="*.mdx" 2>/dev/null | wc -l
grep -rn 'description="[^"]*—[^"]*"' content/ --include="*.mdx" 2>/dev/null | head -5
```

**Pass:** 0 em dashes inside JSX prop strings
**Fail:** any = CRITICAL (causes build failure)

---

## CHECK 13 — Hardcoded secrets

```bash
# Check source files for hardcoded API keys (not .env files)
grep -rn "sk-ant-\|sk-proj-\|AIza\|Bearer [A-Za-z0-9_-]\{20,\}" \
  app/ components/ lib/ scripts/ \
  --include="*.ts" --include="*.tsx" --include="*.js" 2>/dev/null | \
  grep -v "node_modules\|\.next\|example\|placeholder\|YOUR_KEY" | head -10

# Check for tracked .env files
git ls-files | grep "^\.env"
```

**Pass:** 0 hardcoded keys, no .env files in git
**Fail:** any hardcoded key = CRITICAL

---

## CHECK 14 — OpenGraph + sitemap

```bash
grep -n "openGraph\|og:title\|og:image\|twitter:card" app/layout.tsx 2>/dev/null | head -5
ls -la app/sitemap.ts app/sitemap.xml public/sitemap.xml 2>&1 | grep -v "No such"
ls -la app/robots.ts public/robots.txt 2>&1 | grep -v "No such"
```

**Pass:** openGraph in layout, sitemap exists, robots.txt exists
**Fail:** missing openGraph = HIGH | missing sitemap = MEDIUM

---

## CHECK 15 — Build output (optional, slow)

```bash
# Only run this if you want to verify a full production build
# Uncomment to enable:
# npm run build 2>&1 | tail -20
echo "Skipping full build (run manually if needed: npm run build)"
```

---

## CHECK 16 — Git status summary

```bash
git log --oneline -5
git status --short | head -10
```

**Note:** flags any unexpected uncommitted changes.

---

## COMPILE REPORT

```python
python3 - <<'PYEOF'
import os
from datetime import datetime

repo = os.environ.get('SITE_REPO', os.getcwd())
site = os.path.basename(repo)
now = datetime.now().strftime('%Y-%m-%d %H:%M')
report = f"AUDIT-REPORT-{site}-{datetime.now().strftime('%Y-%m-%d')}.md"

template = f"""# Audit Report: {site}
**Date:** {now}
**Repo:** {repo}

---

## Results

| # | Check | Status | Severity | Notes |
|---|-------|--------|----------|-------|
| 1 | TypeScript build | | CRITICAL | |
| 2 | CSS design tokens | | HIGH | |
| 3 | Routing consistency | | MEDIUM | |
| 4 | Broken internal links | | HIGH | |
| 5 | Article structure quality | | MEDIUM | |
| 6 | Meta descriptions | | MEDIUM | |
| 7 | Title lengths | | MEDIUM | |
| 8 | UK English | | LOW | |
| 9 | Banned AI phrases | | LOW | |
| 10 | Em dashes | | LOW | |
| 11 | Author bylines | | MEDIUM | |
| 12 | MDX JSX safety | | CRITICAL | |
| 13 | Hardcoded secrets | | CRITICAL | |
| 14 | OpenGraph + sitemap | | HIGH | |
| 15 | Build output | | — | skipped |
| 16 | Git status | | — | info only |

---

## Issues by severity

### 🔴 CRITICAL (fix before next deploy)

[fill in]

### 🟠 HIGH (fix in next patch)

[fill in]

### 🟡 MEDIUM (fix in next content pass)

[fill in]

### 🟢 LOW (fix when convenient)

[fill in]

---

_Generated by [nextjs-content-audit](https://github.com/YOUR_USERNAME/nextjs-content-audit)_
"""

with open(report, 'w') as f:
    f.write(template)
print(f"Report template saved: {report}")
PYEOF
```
