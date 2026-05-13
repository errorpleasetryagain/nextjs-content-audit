# nextjs-content-audit

A practical audit toolkit for Next.js content sites. Catches the things that silently kill your SEO and affiliate revenue — broken internal links, truncated titles, missing meta descriptions, rogue hardcoded secrets, American spellings creeping into UK-English sites, and more.

Built and battle-tested on [Male Optimal](https://maleoptimal.co.uk), a men's health content site with 300+ MDX articles.

---

## What it checks

16 checks across 4 categories:

**Build health**
- TypeScript compilation errors
- CSS design token integrity
- Routing consistency (e.g. stale route aliases)

**SEO**
- Broken internal links (404 crawler)
- Meta descriptions: missing, over 155 chars, truncated without end punctuation
- Title lengths: anything over 60 chars gets truncated in SERPs
- OpenGraph + sitemap presence

**Content quality**
- Article structure scoring: MDX components, internal links, author bylines
- UK English spot check (American spellings flagged)
- Banned AI phrases (`In conclusion`, `It is worth noting`, `Delve into`, etc.)
- Em dash usage (rewrites needed)

**Security**
- Hardcoded API keys in source files
- `.env` files accidentally tracked in git

Each check outputs a PASS / severity-flagged FAIL. Results compile into a single Markdown report.

---

## Requirements

- Node.js 18+
- Python 3.8+
- A Next.js project with MDX content in `content/` subdirectories
- Articles with YAML frontmatter (`title`, `description`, `author`)

---

## Quick start

```bash
# Clone the toolkit
git clone https://github.com/YOUR_USERNAME/nextjs-content-audit
cd nextjs-content-audit

# Run against your project
SITE_REPO=/path/to/your/nextjs-project python3 audit.py
```

Or run individual scripts:

```bash
# Broken internal links
SITE_REPO=/path/to/project python3 scripts/crawl_404s.py

# Article structure quality scores
SITE_REPO=/path/to/project python3 scripts/audit_structure.py

# SEO: title + description lengths
SITE_REPO=/path/to/project python3 scripts/seo_check.py
```

---

## Configuration

The toolkit works out of the box for projects with this structure:

```
your-project/
├── content/
│   ├── blog/        ← or articles/, guides/, etc.
│   └── guides/
├── app/
├── components/
└── lib/
```

Set `SITE_REPO` to your project root. The scripts auto-detect which content directories exist.

### Customising content directories

Edit the `CONTENT_DIRS` list at the top of each script:

```python
CONTENT_DIRS = ['content/blog', 'content/guides', 'content/articles']
```

### Customising static pages (for 404 crawler)

Edit `STATIC_PAGES` in `crawl_404s.py`:

```python
STATIC_PAGES = ['/', '/blog', '/about', '/contact', '/privacy', '/terms']
```

### Customising banned AI phrases

Edit `BANNED_PHRASES` in `scripts/content_quality.py` — add or remove phrases that don't fit your style guide.

---

## Article structure scoring

`audit_structure.py` scores every MDX article out of 10 based on:

| Check | Points |
|-------|--------|
| `<SebNote>` or equivalent author note component | 2 |
| `<StudyCallout>` or evidence citation component | 2 |
| `<ProductCard>` or comparison component | 2 |
| `<KeyTakeaway>` component | 1 |
| 3+ internal links | 1 |
| Description under 155 chars | 1 |
| Author field set | 1 |

Outputs worst-scoring articles first. Articles under 7/10 are flagged as priority fixes.

The component names are configurable — see `scripts/audit_structure.py`.

---

## The 16-check audit prompt

`AUDIT-PROMPT.md` is a Claude Code prompt that runs all 16 checks in sequence and compiles a consolidated report. Paste it into [Claude Code](https://claude.ai/code) or run with:

```bash
claudex "$(cat AUDIT-PROMPT.md)"
```

With `SITE_REPO` for a different project:

```bash
SITE_REPO=/path/to/other-project claudex "$(cat AUDIT-PROMPT.md)"
```

---

## Example output

```
Running audit on: my-content-site
Report will be saved to: AUDIT-REPORT-my-content-site-2026-05-13.md

CHECK 1 — TypeScript build: ✅ PASS
CHECK 2 — CSS design tokens: ✅ PASS
CHECK 3 — Routing consistency: ✅ PASS
CHECK 4 — Broken internal links: ❌ FAIL (HIGH) — 7 broken links found
CHECK 5 — Article structure: ⚠️  WARN — 23 articles under 7/10
CHECK 6 — Affiliate link audit: ✅ PASS
CHECK 7 — Meta descriptions: ❌ FAIL (MEDIUM) — 14 over 155 chars
CHECK 8 — Title lengths: ❌ FAIL (MEDIUM) — 31 titles over 60 chars
CHECK 9 — UK English: ⚠️  WARN — 4 American spellings
CHECK 10 — Banned phrases: ⚠️  WARN — 2 instances
...

CRITICAL: 0 issues
HIGH: 1 issue (broken internal links)
MEDIUM: 2 issues (meta descriptions, title lengths)
LOW: 2 issues
```

---

## Why title length matters more than you think

We found 31 articles on page 1 of Google with zero clicks. Every one of them had titles over 60 characters — truncated in SERPs to `How to Boost Testosterone Naturally in 2026 | Male ...` instead of the full title. Fixing title lengths across 10 priority pages recovered clicks within 2 weeks.

CHECK 8 in this toolkit catches this automatically.

---

## Affiliate link auditing

If your site uses affiliate programmes (Amazon Associates, Awin, etc.), `audit_structure.py` can cross-reference your tracked partners list against links in your content. Dead or untracked affiliate links are flagged.

See `scripts/audit_affiliate_links.ts` — configure your partner list at the top of the file.

---

## Integrating into CI

The TypeScript affiliate link checker exits with code 1 on failure, making it CI-ready:

```yaml
# .github/workflows/audit.yml
- name: Audit affiliate links
  run: npx tsx scripts/audit_affiliate_links.ts
```

The Python scripts output to stdout and can be piped into CI checks similarly.

---

## Licence

MIT. Use it, fork it, improve it.

---

## Built by

[Male Optimal](https://maleoptimal.co.uk) — evidence-based men's health, built in public.

If this toolkit saves you time, a star helps others find it.
