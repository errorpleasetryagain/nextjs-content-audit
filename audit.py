#!/usr/bin/env python3
"""
audit.py — Main entry point for the nextjs-content-audit toolkit

Runs all Python-based checks in sequence and produces a consolidated report.

Usage:
    python3 audit.py
    SITE_REPO=/path/to/project python3 audit.py
"""

import os
import subprocess
import sys
from datetime import datetime


REPO = os.environ.get("SITE_REPO", os.getcwd())
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")

CHECKS = [
    ("Broken internal links",   "crawl_404s.py",      "HIGH"),
    ("SEO: titles + descriptions", "seo_check.py",    "MEDIUM"),
    ("Article structure quality", "audit_structure.py", "MEDIUM"),
    ("Content quality",         "content_quality.py",  "LOW"),
]


def run_check(name: str, script: str, severity: str) -> dict:
    script_path = os.path.join(SCRIPTS_DIR, script)
    if not os.path.exists(script_path):
        return {"name": name, "status": "SKIP", "severity": severity, "output": "Script not found"}

    env = os.environ.copy()
    env["SITE_REPO"] = REPO

    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        env=env,
    )

    passed = result.returncode == 0
    output = result.stdout + result.stderr

    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "severity": severity,
        "output": output.strip(),
        "returncode": result.returncode,
    }


def main():
    print(f"nextjs-content-audit")
    print(f"Project: {REPO}")
    print(f"{'=' * 60}")
    print()

    if not os.path.exists(REPO):
        print(f"ERROR: SITE_REPO does not exist: {REPO}")
        sys.exit(1)

    results = []

    for name, script, severity in CHECKS:
        print(f"Running: {name}...")
        result = run_check(name, script, severity)
        results.append(result)
        status_icon = "✅" if result["status"] == "PASS" else ("⏭️" if result["status"] == "SKIP" else "❌")
        print(f"{status_icon} {result['status']}")
        if result["status"] == "FAIL":
            # Print first few lines of output on failure
            lines = result["output"].split("\n")[:8]
            for line in lines:
                print(f"   {line}")
        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    failed = [r for r in results if r["status"] == "FAIL"]
    passed = [r for r in results if r["status"] == "PASS"]

    print(f"Passed: {len(passed)} / {len(results)}")
    print(f"Failed: {len(failed)} / {len(results)}")
    print()

    if failed:
        print("Issues found:")
        for r in failed:
            print(f"  [{r['severity']}] {r['name']}")
    else:
        print("✅ All checks passed")

    # Write report
    site_name = os.path.basename(REPO)
    report_path = f"AUDIT-REPORT-{site_name}-{datetime.now().strftime('%Y-%m-%d')}.md"

    with open(report_path, "w") as f:
        f.write(f"# Audit Report: {site_name}\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Project:** {REPO}\n\n---\n\n")
        f.write("## Results\n\n")
        f.write("| Check | Status | Severity |\n|-------|--------|----------|\n")
        for r in results:
            icon = "✅" if r["status"] == "PASS" else ("⏭️" if r["status"] == "SKIP" else "❌")
            f.write(f"| {r['name']} | {icon} {r['status']} | {r['severity']} |\n")

        f.write("\n## Detail\n\n")
        for r in results:
            f.write(f"### {r['name']} ({r['status']})\n\n")
            f.write(f"```\n{r['output'][:2000]}\n```\n\n")

    print(f"\nReport saved: {report_path}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
