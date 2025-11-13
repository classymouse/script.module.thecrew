"""
Small utility to contact Trakt API and attempt to enumerate/inspect available
endpoints. It does not attempt to exhaustively discover every undocumented
route, but:
  - provides a list of common Trakt endpoints (GET/POST)
  - attempts to ping each and report status
  - tries to parse Trakt docs pages for endpoints (best-effort)
Requirements:
  - requests module available
  - set environment variable TRAKT_CLIENT_ID (and optionally TRAKT_ACCESS_TOKEN)
Usage:
  python test.py
"""
from __future__ import annotations

import os
import re
import json
import time
from typing import Dict, List, Optional, Tuple
import requests

TRAKT_API_BASE = "https://api.trakt.tv"
TRAKT_DOCS_URLS = [
    "https://trakt.tv/docs/api",
    "https://trakt.docs.apiary.io/"  # secondary docs host (may redirect)
]

CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("TRAKT_ACCESS_TOKEN")  # optional (OAuth bearer token)


def headers(client_id: Optional[str] = None, token: Optional[str] = None) -> Dict[str, str]:
    cid = client_id or CLIENT_ID
    h = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
    }
    if cid:
        h["trakt-api-key"] = cid
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


COMMON_ENDPOINTS: List[Tuple[str, str]] = [
    # (HTTP_METHOD, PATH)
    ("GET", "/search/movie"),
    ("GET", "/search/show"),
    ("GET", "/search/people"),
    ("GET", "/movies/popular"),
    ("GET", "/movies/trending"),
    ("GET", "/movies/played"),
    ("GET", "/movies/anticipated"),
    ("GET", "/movies/{id}/ratings"),
    ("GET", "/movies/{id}/translations"),
    ("GET", "/shows/popular"),
    ("GET", "/shows/trending"),
    ("GET", "/shows/anticipated"),
    ("GET", "/shows/played"),
    ("GET", "/shows/{id}/seasons"),
    ("GET", "/shows/{id}/people"),
    ("GET", "/shows/{id}/ratings"),
    ("GET", "/seasons/{id}/{season}/episodes"),
    ("GET", "/users/{username}"),
    ("GET", "/users/{username}/watchlist"),
    ("GET", "/users/{username}/watched"),
    ("GET", "/users/{username}/ratings"),
    ("GET", "/sync/watchlist"),
    ("GET", "/sync/history"),
    ("POST", "/sync/watchlist"),
    ("POST", "/sync/history"),
    ("POST", "/scrobble/start"),
    ("POST", "/scrobble/stop"),
    ("POST", "/oauth/token"),
]


def call_trakt(method: str, path: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Tuple[int, Optional[Dict]]:
    """Call trakt API and return (status_code, parsed_json_or_none)."""
    url = TRAKT_API_BASE + path
    try:
        resp = requests.request(method, url, headers=headers(), params=params or {}, json=body, timeout=12)
    except Exception as e:
        return 0, {"error": str(e)}
    try:
        data = resp.json() if resp.text else None
    except Exception:
        data = {"raw": resp.text[:200]}
    return resp.status_code, data


def ping_common_endpoints(limit: int = 30) -> Dict[str, Dict]:
    """Ping the common endpoints list and summarize results.
    For endpoints with placeholders, try a few common substitutions.
    """
    subs = {
        "{id}": "game-of-thrones",
        "{username}": "trakt",  # public test user
        "{season}": "1"
    }

    results: Dict[str, Dict] = {}
    counter = 0
    for method, path in COMMON_ENDPOINTS:
        if counter >= limit:
            break
        counter += 1
        test_path = path
        for key, val in subs.items():
            if key in test_path:
                test_path = test_path.replace(key, val)
        status, data = call_trakt(method, test_path)
        results[f"{method} {path}"] = {"tested_path": test_path, "status": status, "keys": sorted((data.keys() if isinstance(data, dict) else [])) if data else None}
    return results


def discover_from_docs() -> List[str]:
    """Best-effort parse of Trakt docs to extract API path patterns.
    This scrapes docs pages for "/..." patterns. Not guaranteed complete."""
    found = set()
    for docs_url in TRAKT_DOCS_URLS:
        try:
            r = requests.get(docs_url, timeout=10)
            text = r.text
            # Find strings that look like paths: "/users/{username}/watchlist" or "/movies/trending"
            for m in re.finditer(r'(["\'])(/[\w\-\{\}/]+)(["\'])', text):
                found.add(m.group(2))
            # also capture plain occurrences
            for m in re.finditer(r'(?m)^\s*(GET|POST|PUT|DELETE|PATCH)\s+(/[\w\-\{\}/]+)', text):
                found.add(m.group(2))
        except Exception:
            continue
    return sorted(found)


def main() -> None:
    print("Trakt API quick enumerator")
    if not CLIENT_ID:
        print("WARNING: TRAKT_CLIENT_ID not set. Many endpoints will 401. Set TRAKT_CLIENT_ID env var.")
    else:
        print("Using TRAKT_CLIENT_ID from environment.")

    print("\n--- Ping common endpoints ---")
    res = ping_common_endpoints()
    for k, v in res.items():
        print(f"{k:40s} -> status={v['status']:3d} tested={v['tested_path']}")
        if v["keys"]:
            print(f"    keys: {', '.join(v['keys'][:8])}")

    print("\n--- Discover endpoints from docs (best effort) ---")
    docs_endpoints = discover_from_docs()
    if docs_endpoints:
        for p in docs_endpoints[:120]:
            print("  " + p)
    else:
        print("  (no endpoints discovered from docs)")

    print("\n--- Done ---\n")


if __name__ == "__main__":
    main()