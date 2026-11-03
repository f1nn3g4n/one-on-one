#!/usr/bin/env python3
"""Collect the user's GitHub PR activity for a period via the gh CLI.

  github_activity.py --config CONFIG --start YYYY-MM-DD --end YYYY-MM-DD

Prints the `code` block of raw.json (see references/data-schema.md) when
`platforms.code` is github. Preferred over the GitHub connector because only
the REST timeline exposes ready-for-review times.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, timedelta

TICKET_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d+)\b")


def gh_json(args):
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:3])} failed: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout or "null")


def api(path):
    # --paginate concatenates JSON arrays page by page; --slurp merges them into one list of pages.
    pages = gh_json(["api", path, "--paginate", "--slurp"])
    if isinstance(pages, list) and pages and isinstance(pages[0], list):
        return [item for page in pages for item in page]
    return pages[0] if isinstance(pages, list) and len(pages) == 1 else pages


def search(flag, login, org, start):
    return gh_json([
        "search", "prs", flag, login, "--owner", org, "--updated", f">={start}",
        "--limit", "200", "--json", "repository,number",
    ])


def in_range(ts, start, end):
    # Coarse UTC date filter; metrics.py applies the exact local-time period.
    return ts is not None and start <= ts[:10] <= end


def is_bot(user):
    return (user or {}).get("type") == "Bot" or (user or {}).get("login", "").endswith("[bot]")


def activity(repo, number, login, commits):
    """Who did what when on the user's PR, for PR Churn. Commits use the committer
    date, which a rebase or amend resets to roughly when it was pushed; the author
    date can be days older. Other people are recorded only as "other", never by name."""
    def by(user):
        return "bot" if is_bot(user) else "author" if user["login"] == login else "other"

    events = [{"at": c["commit"]["committer"]["date"], "kind": "commit", "by": "author", "state": None, "has_text": None}
              for c in commits]
    for r in api(f"repos/{repo}/pulls/{number}/reviews"):
        if r.get("submitted_at") and r.get("user"):
            # An approval with no text asks nothing of the author, so it ends a review
            # wait without starting a response wait.
            events.append({"at": r["submitted_at"], "kind": "review", "by": by(r["user"]), "state": r["state"],
                           "has_text": bool((r.get("body") or "").strip())})
    for path in (f"repos/{repo}/pulls/{number}/comments", f"repos/{repo}/issues/{number}/comments"):
        for c in api(path):
            if c.get("user"):
                events.append({"at": c["created_at"], "kind": "comment", "by": by(c["user"]), "state": None, "has_text": True})
    return sorted(events, key=lambda e: e["at"])


def set_first_commits(prs):
    """Stacked PRs list their parent's commits too (and again after the parent is
    squash-merged and the base retargets), so a commit only counts toward the
    earliest-opened PR that contains it. Commits are keyed by author date and
    subject rather than SHA because rebasing a stack rewrites SHAs but keeps both.
    Parents opened before the collection window aren't seen, so their commits can
    still leak into a child's first_commit_at."""
    claimed = set()
    for pr in sorted(prs, key=lambda p: p["created_at"]):
        own = [c for c in pr.pop("_commits") if c not in claimed]
        claimed.update(own)
        pr["first_commit_at"] = min(c[0] for c in own) if own else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True, help="inclusive")
    args = parser.parse_args(argv)

    with open(os.path.expanduser(args.config)) as f:
        config = json.load(f)
    login = config["code"]["user"]
    # Pad by a day so timezone edges survive; metrics.py does the exact cut.
    lo = (date.fromisoformat(args.start) - timedelta(days=1)).isoformat()
    hi = (date.fromisoformat(args.end) + timedelta(days=1)).isoformat()

    authored, reviewed, commented = set(), set(), set()
    for org in config["code"]["orgs"]:
        for flag, bucket in (("--author", authored), ("--reviewed-by", reviewed), ("--commenter", commented)):
            for pr in search(flag, login, org, args.start):
                bucket.add((pr["repository"]["nameWithOwner"], pr["number"]))

    result = {"prs_authored": [], "reviews": [], "comments": []}
    for repo, number in sorted(authored | reviewed | commented):
        pr = api(f"repos/{repo}/pulls/{number}")
        author = pr["user"]["login"]
        url = pr["html_url"]

        if author == login:
            ready_at = None
            if not pr.get("draft"):
                events = api(f"repos/{repo}/issues/{number}/timeline")
                ready_events = [e["created_at"] for e in events if e.get("event") == "ready_for_review"]
                # Never-drafted PRs have no event; they were ready when opened.
                ready_at = min(ready_events) if ready_events else pr["created_at"]
            state = "merged" if pr.get("merged_at") else pr["state"]
            raw_commits = api(f"repos/{repo}/pulls/{number}/commits")
            commits = [(c["commit"]["author"]["date"], c["commit"]["message"].split("\n", 1)[0]) for c in raw_commits]
            result["prs_authored"].append({
                "repo": repo, "number": number, "title": pr["title"], "url": url,
                "state": state, "created_at": pr["created_at"], "ready_at": ready_at,
                "first_commit_at": None, "_commits": commits,
                "merged_at": pr.get("merged_at"),
                "additions": pr.get("additions"), "deletions": pr.get("deletions"),
                "ticket_ids": sorted(set(TICKET_RE.findall(pr["title"] + " " + pr["head"]["ref"].upper()))),
                "activity": activity(repo, number, login, raw_commits),
            })
            continue

        review_comments = api(f"repos/{repo}/pulls/{number}/comments")
        counts = {}
        for c in review_comments:
            if c["user"]["login"] == login and c.get("pull_request_review_id"):
                counts[c["pull_request_review_id"]] = counts.get(c["pull_request_review_id"], 0) + 1
        for r in api(f"repos/{repo}/pulls/{number}/reviews"):
            if r["user"]["login"] != login or not in_range(r.get("submitted_at"), lo, hi):
                continue
            result["reviews"].append({
                "repo": repo, "number": number, "title": pr["title"], "url": url, "author": author,
                "state": r["state"], "submitted_at": r["submitted_at"], "comment_count": counts.get(r["id"], 0),
            })
        for c in api(f"repos/{repo}/issues/{number}/comments"):
            if c["user"]["login"] == login and in_range(c["created_at"], lo, hi):
                result["comments"].append({
                    "repo": repo, "number": number, "title": pr["title"], "url": c["html_url"],
                    "created_at": c["created_at"], "body": c["body"],
                })

    set_first_commits(result["prs_authored"])
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
