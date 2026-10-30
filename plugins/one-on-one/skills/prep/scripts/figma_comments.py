#!/usr/bin/env python3
"""Fetch the user's own Figma comments for a period.

  figma_comments.py whoami
  figma_comments.py comments --config CONFIG --start YYYY-MM-DD --end YYYY-MM-DD --file URL [--file URL ...]

The Figma MCP connector exposes design context, not comments, so this calls the
REST API with a personal access token in FIGMA_TOKEN (scopes: current_user:read,
file_comments:read, file_content:read). Figma has no "comments by user" endpoint,
and listing team projects needs a projects:read scope that personal tokens may
not offer, so the files to scan are passed in per run. The set of files someone
comments on changes too often to keep in config.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://api.figma.com/v1"
# Branch URLs (/design/<key>/branch/<branch key>/) keep comments on the main file's key.
FILE_URL_RE = re.compile(r"figma\.com/(?:design|file|board|proto|slides)/([A-Za-z0-9]+)")


def require_ssl():
    # Without this, a Python built against a since-removed OpenSSL fails deep in
    # urllib with "unknown url type: https", which reads like a bad URL.
    try:
        import ssl  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            f"{sys.executable} (Python {sys.version.split()[0]}) has no working SSL support, "
            f"so it can't call the Figma API: {e}\n"
            "Rebuild this Python or run the script with an interpreter that has SSL, "
            "e.g. /opt/homebrew/bin/python3."
        )


def get(path):
    require_ssl()
    token = os.environ.get("FIGMA_TOKEN")
    if not token:
        raise SystemExit("FIGMA_TOKEN is not set")
    req = urllib.request.Request(API + path, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Figma API {e.code} on {path}: {e.read().decode(errors='replace')[:200]}")


def parse_ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def file_key(ref):
    match = FILE_URL_RE.search(ref)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", ref):
        return ref
    raise SystemExit(f"Not a Figma file URL or key: {ref}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    c = sub.add_parser("comments")
    c.add_argument("--config", required=True)
    c.add_argument("--start", required=True)
    c.add_argument("--end", required=True, help="inclusive")
    c.add_argument("--file", action="append", required=True, help="Figma file URL or key; repeat for each file")
    args = parser.parse_args(argv)

    if args.cmd == "whoami":
        me = get("/me")
        print(json.dumps({"id": me.get("id"), "handle": me.get("handle"), "email": me.get("email")}))
        return 0

    with open(os.path.expanduser(args.config)) as f:
        config = json.load(f)
    user_id = config.get("design", {}).get("user_id") or get("/me")["id"]
    # A day of padding on each side because Figma timestamps are UTC and the period is local.
    lo = datetime.combine(date.fromisoformat(args.start) - timedelta(days=1), datetime.min.time(), timezone.utc)
    hi = datetime.combine(date.fromisoformat(args.end) + timedelta(days=2), datetime.min.time(), timezone.utc)

    out = []
    for key in dict.fromkeys(file_key(f) for f in args.file):
        data = get(f"/files/{key}/comments")
        name = get(f"/files/{key}?depth=1").get("name", key)
        for cm in data.get("comments", []):
            if cm.get("user", {}).get("id") != user_id:
                continue
            created = parse_ts(cm["created_at"])
            if not (lo <= created < hi):
                continue
            out.append({
                "file_name": name,
                "file_url": f"https://www.figma.com/design/{key}?comment={cm['id']}",
                "created_at": cm["created_at"],
                "body": cm.get("message", ""),
                "is_reply": bool(cm.get("parent_id")),
            })
    print(json.dumps(sorted(out, key=lambda c: c["created_at"]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
