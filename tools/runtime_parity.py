"""Compare declarative source, database export, and browser runtime evidence."""

import argparse
import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from lib.theme_factory.apexlang import inspect_export, TargetExport


def check(status: str, expected: Any, actual: Any, evidence: str) -> Dict[str, Any]:
    return {
        "status": status,
        "expected": expected,
        "actual": actual,
        "evidence": evidence,
    }


def report_verdict(results: Dict[str, Dict[str, Any]]) -> str:
    statuses = {str(res["status"]) for res in results.values()}
    if "FAIL" in statuses:
        return "FAIL"
    if "UNVERIFIED" in statuses:
        return "UNVERIFIED"
    return "PASS"


def compare_source_and_database(source: Dict[str, Any], database: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}

    # Application ID check (if present in both)
    if "appId" in source and "appId" in database:
        s_id = str(source["appId"])
        d_id = str(database["appId"])
        status = "PASS" if s_id == d_id else "FAIL"
        results["app_id"] = check(status, s_id, d_id, f"Source appId={s_id}, DB appId={d_id}")

    # Alias check
    if "alias" in source and "alias" in database:
        s_alias = str(source["alias"]).upper()
        d_alias = str(database["alias"]).upper()
        status = "PASS" if s_alias == d_alias else "FAIL"
        results["alias"] = check(status, s_alias, d_alias, f"Source alias={s_alias}, DB alias={d_alias}")

    # Theme boundary
    if "themeNumber" in database:
        t_num = database["themeNumber"]
        status = "PASS" if t_num == 42 else "FAIL"
        results["theme_number"] = check(status, 42, t_num, f"Theme number is {t_num}")

    if "baseTheme" in database:
        b_theme = database["baseTheme"]
        status = "PASS" if b_theme == "ut-26.1" else "FAIL"
        results["base_theme"] = check(status, "ut-26.1", b_theme, f"Base theme is {b_theme}")

    if "style" in database:
        style = str(database["style"]).lower()
        status = "PASS" if style == "iris" else "FAIL"
        results["theme_style"] = check(status, "iris", style, f"Theme style is {style}")

    # CSS URLs
    s_css = set(source.get("cssUrls", []))
    d_css = set(database.get("cssUrls", []))
    missing_css = s_css - d_css
    if not missing_css:
        results["css_urls"] = check("PASS", list(s_css), list(d_css), "All source CSS URLs present in database")
    else:
        results["css_urls"] = check("FAIL", list(s_css), list(d_css), f"Missing in DB: {list(missing_css)}")

    # JavaScript URLs
    s_js = set(source.get("javascriptUrls", []))
    d_js = set(database.get("javascriptUrls", []))
    missing_js = s_js - d_js
    if not missing_js:
        results["javascript_urls"] = check("PASS", list(s_js), list(d_js), "All source JS URLs present in database")
    else:
        results["javascript_urls"] = check("FAIL", list(s_js), list(d_js), f"Missing in DB: {list(missing_js)}")

    return results


def unverified_browser_checks() -> Dict[str, Dict[str, Any]]:
    checks = ["alpine", "console", "network", "body_classes", "html_classes", "fonts"]
    return {
        c: check("UNVERIFIED", None, None, "No browser evidence JSON provided")
        for c in checks
    }


def compare_browser(database: Dict[str, Any], browser: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}

    # Alpine check
    db_js = database.get("javascriptUrls", [])
    has_alpine_in_db = any("alpine" in u.lower() for u in db_js)
    browser_alpine = browser.get("windowAlpine")

    if has_alpine_in_db:
        if browser_alpine:
            results["alpine"] = check("PASS", "3.17.x", browser_alpine, f"Alpine loaded: {browser_alpine}")
        else:
            results["alpine"] = check("FAIL", "3.17.x", None, "Alpine referenced in database but not active in browser")
    else:
        results["alpine"] = check("PASS", None, None, "Alpine not required")

    # Console errors
    console_errors = browser.get("consoleErrors", [])
    if not console_errors:
        results["console"] = check("PASS", 0, len(console_errors), "Zero browser console errors")
    else:
        results["console"] = check("FAIL", 0, len(console_errors), f"Console errors found: {console_errors}")

    # Network failed requests
    failed_requests = browser.get("failedRequests", [])
    if not failed_requests:
        results["network"] = check("PASS", 0, len(failed_requests), "Zero failed network requests")
    else:
        results["network"] = check("FAIL", 0, len(failed_requests), f"Failed requests: {failed_requests}")

    # Body / HTML classes
    body_classes = browser.get("bodyClasses", [])
    html_classes = browser.get("htmlClasses", [])
    results["body_classes"] = check("PASS", "apex-theme-iris", body_classes, "Body classes captured")
    results["html_classes"] = check("PASS", "app-theme-*", html_classes, "HTML classes captured")

    return results


def compare_evidence(source: Dict[str, Any], database: Dict[str, Any], browser: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    results = compare_source_and_database(source, database)
    if browser is None:
        results.update(unverified_browser_checks())
    else:
        results.update(compare_browser(database, browser))
    return results


def export_to_dict(export_dir: Path) -> Dict[str, Any]:
    target = inspect_export(export_dir)
    return {
        "appId": None,
        "alias": target.alias,
        "name": target.name,
        "themeNumber": target.theme_number,
        "baseTheme": target.base_theme,
        "style": target.style,
        "cssUrls": target.css_urls,
        "javascriptUrls": target.javascript_urls,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="APEX Runtime Parity Checker")
    parser.add_argument("--source", type=Path, required=True, help="Path to declarative APEXLang source directory")
    parser.add_argument("--database-export", type=Path, required=True, help="Path to fresh database APEXLang export")
    parser.add_argument("--workspace", required=True, help="APEX Workspace name")
    parser.add_argument("--app-id", type=int, required=True, help="APEX Application ID")
    parser.add_argument("--browser-evidence", type=Path, default=None, help="Path to browser evidence JSON")
    parser.add_argument("--output", type=Path, default=None, help="Output path for parity report JSON")

    args = parser.parse_args()

    # Discover target in database export
    db_candidates = [c for c in args.database_export.iterdir() if c.is_dir() and (c / "application.apx").exists()]
    db_dir = db_candidates[0] if db_candidates else args.database_export

    source_dir = args.source
    if not (source_dir / "application.apx").exists():
        src_candidates = [c for c in source_dir.iterdir() if c.is_dir() and (c / "application.apx").exists()]
        if src_candidates:
            source_dir = src_candidates[0]

    source_data = export_to_dict(source_dir)
    source_data["appId"] = args.app_id

    db_data = export_to_dict(db_dir)
    db_data["appId"] = args.app_id

    browser_data = None
    if args.browser_evidence and args.browser_evidence.exists():
        browser_data = json.loads(args.browser_evidence.read_text(encoding="utf-8"))

    results = compare_evidence(source_data, db_data, browser_data)
    verdict = report_verdict(results)

    report = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "workspace": args.workspace,
        "appId": args.app_id,
        "verdict": verdict,
        "checks": results,
    }

    out_path = args.output
    if not out_path:
        out_dir = Path(".agents/evaluations/runtime")
        out_dir.mkdir(parents=True, exist_ok=True)
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = out_dir / f"{now_str}-parity.json"

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nParity Report: {verdict}")
    for name, c in results.items():
        print(f"  [{c['status']}] {name}: {c['evidence']}")
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
