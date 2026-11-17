#!/usr/bin/env python3
"""Deterministic metrics for a 1-1 prep run.

  metrics.py compute --raw RAW --config CONFIG --runs-dir DIR --out OUT
  metrics.py previous --runs-dir DIR --before YYYY-MM-DD

Stdlib only (Python 3.9+) so it runs anywhere the plugin is installed.
"""
import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

# Working days per point, from the team's loose sizing guideline: 0 is "less than
# a day", 3 is "a few days", 5 is "a week", and 8 ("more than a week") uses its
# lower bound, so 8-pointers are judged generously.
DEFAULT_POINTS_TO_DAYS = {"0": 0.5, "1": 1, "2": 2, "3": 3, "5": 5, "8": 8}
DEFAULT_THRESHOLDS = {"ahead": 0.8, "over": 1.2}
DEFAULT_REVIEW_STATES = ["In Review", "Code Review", "Ready for Review"]
# Below this many measured tickets a pace is mostly noise, so open work is projected at face value.
MIN_PACE_TICKETS = 3

# Release branch merges replay a whole release's diff, so they swamp the user's own line counts.
RELEASE_MERGE_RE = re.compile(r"\bmerge release/", re.IGNORECASE)

TREND_KEYS = ["prs_merged", "reviews_given", "tickets_completed", "points_completed", "design_comments",
              "pr_open_to_merge_hours", "draft_hours", "first_review_hours", "in_review_hours",
              "approval_to_merge_hours"]
# Runs saved before the data format was named by role still hold these keys.
LEGACY_TOTALS = {"tickets_completed": "linear_completed", "design_comments": "figma_comments"}


def parse_ts(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def period_bounds(period, tz):
    """Inclusive local dates → [start, end) aware datetimes, so 'end' covers the whole last day."""
    start = datetime.combine(date.fromisoformat(period["start"]), time.min, tz)
    end = datetime.combine(date.fromisoformat(period["end"]) + timedelta(days=1), time.min, tz)
    return start, end


def in_period(value, bounds):
    dt = parse_ts(value)
    return dt is not None and bounds[0] <= dt < bounds[1]


def working_days_between(start, end, tz):
    """Elapsed weekday time in days. Counts 24h per weekday rather than office hours,
    which matches how the sizing guideline is talked about ("about two days")."""
    return round(weekday_seconds(start, end, tz) / 86400, 2)


def weekday_seconds(start, end, tz):
    if end <= start:
        return 0.0
    start, end = start.astimezone(tz), end.astimezone(tz)
    total = timedelta()
    cur = start
    while cur < end:
        next_midnight = datetime.combine(cur.date() + timedelta(days=1), time.min, tz)
        step_end = min(end, next_midnight)
        if cur.weekday() < 5:
            total += step_end - cur
        cur = step_end
    return total.total_seconds()


def week_start(dt, tz):
    local = dt.astimezone(tz).date()
    return (local - timedelta(days=local.weekday())).isoformat()


def points_key(estimate):
    return str(int(estimate)) if float(estimate).is_integer() else str(estimate)


def estimate_rows(raw, config, bounds, tz):
    sizing = config.get("estimates", {})
    mapping = sizing.get("points_to_days") or DEFAULT_POINTS_TO_DAYS
    thresholds = {**DEFAULT_THRESHOLDS, **sizing.get("thresholds", {})}

    prs_by_url = {}
    prs_by_ticket = defaultdict(list)
    for pr in raw.get("code", {}).get("prs_authored", []):
        prs_by_url[pr["url"]] = pr
        for ticket in pr.get("ticket_ids", []):
            prs_by_ticket[ticket].append(pr)

    rows = []
    for issue in raw.get("tickets", {}).get("issues", []):
        if issue.get("estimate") is None:
            continue
        linked = {p["url"]: p for p in prs_by_ticket.get(issue["identifier"], [])}
        linked.update({u: prs_by_url[u] for u in issue.get("pr_urls", []) if u in prs_by_url})
        in_progress = parse_ts(issue.get("in_progress_at"))
        first_commit = min(filter(None, (parse_ts(p.get("first_commit_at")) for p in linked.values())), default=None)
        # Tracker integrations (Linear's, Jira's) can flip tickets to In Progress when the PR opens,
        # which is often after the work started, so the first commit can be earlier.
        starts = [t for t in (in_progress, first_commit) if t is not None]
        if not starts:
            continue
        started = min(starts)
        candidates = [r for r in (parse_ts(p.get("ready_at")) for p in linked.values()) if r is not None]
        candidates = [c for c in candidates if c >= started]
        row = {
            "ticket": issue["identifier"],
            "title": issue.get("title"),
            "url": issue.get("url"),
            "points": issue["estimate"],
            "started_at": started.isoformat(),
            "start_source": "first_commit" if started == first_commit and started != in_progress else "in_progress",
        }
        expected = mapping.get(points_key(issue["estimate"]))
        if not candidates:
            # Only report tickets the user actually touched this period.
            if bounds[0] <= started < bounds[1]:
                rows.append({**row, "status": "no_ready_time"})
            continue
        ready = min(candidates)
        if not (bounds[0] <= ready < bounds[1]):
            continue
        actual = working_days_between(started, ready, tz)
        row.update(ready_at=ready.isoformat(), actual_days=actual)
        if expected is None:
            rows.append({**row, "status": "unmapped"})
            continue
        ratio = round(actual / expected, 2) if expected else None
        if ratio is None:
            status = "unmapped"
        elif ratio <= thresholds["ahead"]:
            status = "ahead"
        elif ratio > thresholds["over"]:
            status = "over"
        else:
            status = "on_track"
        rows.append({**row, "expected_days": expected, "ratio": ratio, "status": status})
    return sorted(rows, key=lambda r: r["ticket"])


def cycle_outlook(raw, config, bounds, tz, estimates):
    """Progress through the current cycle or sprint and whether the open work assigned
    to the user fits in the working days left, as of the end of the period."""
    cycle = raw.get("tickets", {}).get("cycle")
    if not cycle or not cycle.get("starts_at") or not cycle.get("ends_at"):
        return None
    sizing = config.get("estimates", {})
    mapping = sizing.get("points_to_days") or DEFAULT_POINTS_TO_DAYS
    thresholds = {**DEFAULT_THRESHOLDS, **sizing.get("thresholds", {})}
    starts, ends = parse_ts(cycle["starts_at"]), parse_ts(cycle["ends_at"])
    as_of = max(starts, min(bounds[1], ends))

    # Scale remaining estimates by how this period's tickets actually went, so someone
    # who runs consistently fast or slow isn't projected at face value. The median keeps
    # one ticket that ran 6x over from doubling the projection for everything else.
    ratios = [e["ratio"] for e in estimates if e.get("ratio") is not None]
    pace = round(statistics.median(ratios), 2) if len(ratios) >= MIN_PACE_TICKETS else None

    # A ticket whose PR is up for review has used its estimate (that's where actuals stop),
    # so it shouldn't count as work left or as running past its estimate.
    review_states = {s.lower() for s in config.get("tickets", {}).get("review_states") or DEFAULT_REVIEW_STATES}
    ready_prs = {p["url"]: p for p in raw.get("code", {}).get("prs_authored", [])
                 if p.get("ready_at") or p.get("state") == "merged"}
    ready_tickets = {i for p in ready_prs.values() for i in p.get("ticket_ids", [])}
    ready_tickets |= {i["identifier"] for i in raw.get("tickets", {}).get("issues", [])
                      if any(u in ready_prs for u in i.get("pr_urls") or [])}

    issues = [i for i in cycle.get("issues", []) if i.get("status_type") != "canceled"]
    done = [i for i in issues if i.get("status_type") == "completed"]
    open_issues = [i for i in issues if i.get("status_type") != "completed"]
    in_review = [i for i in open_issues
                 if (i.get("status") or "").lower() in review_states or i["identifier"] in ready_tickets]
    remaining = []
    for issue in open_issues:
        if issue.get("estimate") is None or issue in in_review:
            continue
        expected = mapping.get(points_key(issue["estimate"]))
        if expected is None:
            continue
        started = parse_ts(issue.get("started_at"))
        worked = working_days_between(started, as_of, tz) if started else 0.0
        budget = expected * (pace or 1.0)
        remaining.append({
            "ticket": issue["identifier"],
            "title": issue.get("title"),
            "url": issue.get("url"),
            "points": issue["estimate"],
            "worked_days": worked,
            "remaining_days": round(max(budget - worked, 0.0), 2),
            # Clamped to zero above, so flag these or a stuck ticket would look free.
            "past_estimate": worked > budget,
        })

    days_left = working_days_between(as_of, ends, tz)
    projected = round(sum(r["remaining_days"] for r in remaining), 2)
    if days_left == 0:
        status = "ended" if not remaining else "over"
        load = None
    else:
        load = round(projected / days_left, 2)
        status = ("under" if load <= thresholds["ahead"]
                  else "over" if load > thresholds["over"] else "on_track")

    return {
        "id": cycle.get("id"),
        "number": cycle.get("number"),
        "name": cycle.get("name"),
        "team": cycle.get("team"),
        "starts_at": starts.isoformat(),
        "ends_at": ends.isoformat(),
        "mid_cycle": as_of < ends,
        "working_days_total": working_days_between(starts, ends, tz),
        "working_days_elapsed": working_days_between(starts, as_of, tz),
        "working_days_left": days_left,
        "points_completed": sum(i.get("estimate") or 0 for i in done),
        "points_open": sum(i.get("estimate") or 0 for i in open_issues),
        "tickets_completed": len(done),
        "tickets_open": len(open_issues),
        "tickets_in_review": len(in_review),
        "points_in_review": sum(i.get("estimate") or 0 for i in in_review),
        "unestimated_open": sum(1 for i in open_issues if i.get("estimate") is None),
        "pace": pace,
        "projected_days": projected,
        "load": load,
        "status": status,
        "remaining": sorted(remaining, key=lambda r: -r["remaining_days"]),
    }


def summarize(hours):
    if not hours:
        return {"count": 0, "average_hours": None, "median_hours": None, "max_hours": None}
    return {"count": len(hours), "average_hours": round(sum(hours) / len(hours), 1),
            "median_hours": round(statistics.median(hours), 1), "max_hours": round(max(hours), 1)}


STAGES = ["draft", "first_review", "in_review", "approval_to_merge"]


def pr_churn(raw, bounds, tz):
    """Where the user's merged PRs spent their time, stage by stage:
    created → ready for review → first review from someone else → last approval → merged.
    Hours are weekday hours (24 per weekday), like the estimates. Bots and the author
    never count as a review. A stage whose end never happened (merged with no approval)
    is left out rather than folded into a neighbour, and the PR is counted under `skipped`."""
    def hours(a, b):
        return round(weekday_seconds(a, b, tz) / 3600, 1)

    stages = {k: [] for k in STAGES}
    totals, rows, open_prs = [], [], []
    skipped = {"no_review": 0, "no_approval": 0}
    for pr in raw.get("code", {}).get("prs_authored", []):
        if RELEASE_MERGE_RE.search(pr.get("title") or ""):
            continue
        created, ready, merged = (parse_ts(pr.get(k)) for k in ("created_at", "ready_at", "merged_at"))
        end = merged or bounds[1]
        reviews = [e for e in pr.get("activity") or []
                   if e["by"] == "other" and e["kind"] in ("review", "comment")
                   and ready is not None and ready <= parse_ts(e["at"]) <= end]
        first_review = parse_ts(reviews[0]["at"]) if reviews else None
        approvals = [parse_ts(e["at"]) for e in reviews if e.get("state") == "APPROVED"]
        last_approval = approvals[-1] if approvals else None

        if merged is None:
            if pr.get("state") == "open":
                stage, since = (("draft", created) if ready is None
                                else ("first_review", ready) if first_review is None
                                else ("in_review", first_review) if last_approval is None
                                else ("approval_to_merge", last_approval))
                open_prs.append({"repo": pr["repo"], "number": pr["number"], "title": pr.get("title"),
                                 "url": pr.get("url"), "stage": stage, "hours_in_stage": hours(since, bounds[1])})
            continue
        if not bounds[0] <= merged < bounds[1]:
            continue

        row = {"repo": pr["repo"], "number": pr["number"], "title": pr.get("title"), "url": pr.get("url"),
               "open_to_merge_hours": hours(created, merged)}
        row["draft"] = hours(created, ready or created)
        if first_review is None:
            skipped["no_review"] += 1
            row.update(first_review=None, in_review=None, approval_to_merge=None)
        else:
            row["first_review"] = hours(ready, first_review)
            if last_approval is None:
                skipped["no_approval"] += 1
                row.update(in_review=None, approval_to_merge=None)
            else:
                row["in_review"] = hours(first_review, last_approval)
                row["approval_to_merge"] = hours(last_approval, merged)
        for k in STAGES:
            if row[k] is not None:
                stages[k].append(row[k])
        totals.append(row["open_to_merge_hours"])
        rows.append(row)
    return {
        **{k: summarize(v) for k, v in stages.items()},
        "open_to_merge": summarize(totals),
        "skipped": skipped,
        "open_prs": sorted(open_prs, key=lambda o: -o["hours_in_stage"]),
        "prs": sorted(rows, key=lambda r: -r["open_to_merge_hours"]),
    }


def compute(raw, config, previous):
    tz_name = config.get("timezone")
    tz = ZoneInfo(tz_name) if tz_name and ZoneInfo else timezone.utc
    bounds = period_bounds(raw["period"], tz)
    gh = raw.get("code", {})
    ln = raw.get("tickets", {})
    fg = raw.get("design", {})
    sl = raw.get("messages", {})

    prs = gh.get("prs_authored", [])
    opened = [p for p in prs if in_period(p.get("created_at"), bounds)]
    merged = [p for p in prs if p.get("state") == "merged" and in_period(p.get("merged_at"), bounds)]
    reviews = [r for r in gh.get("reviews", []) if in_period(r.get("submitted_at"), bounds)]
    gh_comments = [c for c in gh.get("comments", []) if in_period(c.get("created_at"), bounds)]
    completed = [i for i in ln.get("issues", []) if in_period(i.get("completed_at"), bounds)]
    ln_comments = [c for c in ln.get("comments", []) if in_period(c.get("created_at"), bounds)]
    design_comments = [c for c in fg.get("comments", []) if in_period(c.get("created_at"), bounds)]
    # Collection pads the search by a day each side; a conversation counts if any of it fell in the period.
    convos = [c for c in sl.get("conversations", [])
                    if in_period(c.get("first_at"), bounds) or in_period(c.get("last_at"), bounds)]
    convo_categories = defaultdict(int)
    for c in convos:
        convo_categories[c.get("category", "other")] += 1

    review_states = defaultdict(int)
    for r in reviews:
        review_states[r.get("state", "UNKNOWN")] += 1

    totals = {
        "prs_opened": len(opened),
        "prs_merged": len(merged),
        "lines_added": sum(p.get("additions") or 0 for p in merged if not RELEASE_MERGE_RE.search(p["title"])),
        "lines_removed": sum(p.get("deletions") or 0 for p in merged if not RELEASE_MERGE_RE.search(p["title"])),
        "release_merges": sum(1 for p in merged if RELEASE_MERGE_RE.search(p["title"])),
        # One person can submit several reviews on the same PR; managers think in PRs reviewed.
        "reviews_given": len({(r["repo"], r["number"]) for r in reviews}),
        "review_submissions": len(reviews),
        "review_states": dict(sorted(review_states.items())),
        "review_comments": sum(r.get("comment_count") or 0 for r in reviews),
        "pr_comments": len(gh_comments),
        "repos_touched": len({p["repo"] for p in opened + merged} | {r["repo"] for r in reviews}
                             | {c["repo"] for c in gh_comments}),
        "tickets_completed": len(completed),
        "points_completed": sum(i.get("estimate") or 0 for i in completed),
        "ticket_comments": len(ln_comments),
        "design_comments": len(design_comments),
        "design_files": len({c.get("file_url") for c in design_comments}),
        "messages_sent": sl.get("my_messages", 0),
        "conversations": len(convos),
        "conversations_by_category": dict(sorted(convo_categories.items())),
    }

    by_repo = defaultdict(lambda: {"prs": 0, "reviews": 0, "comments": 0})
    for p in {(p["repo"], p["number"]): p for p in opened + merged}.values():
        by_repo[p["repo"]]["prs"] += 1
    for repo, _ in {(r["repo"], r["number"]) for r in reviews}:
        by_repo[repo]["reviews"] += 1
    for c in gh_comments:
        by_repo[c["repo"]]["comments"] += 1
    activity_by_repo = sorted(
        ({"repo": k, **v} for k, v in by_repo.items()),
        key=lambda r: -(r["prs"] + r["reviews"] + r["comments"]),
    )

    weeks = {}
    cur = bounds[0]
    while cur < bounds[1]:
        weeks[week_start(cur, tz)] = {"prs_merged": 0, "reviews": 0, "tickets_completed": 0}
        cur += timedelta(days=7)
    weeks.setdefault(week_start(bounds[1] - timedelta(seconds=1), tz),
                     {"prs_merged": 0, "reviews": 0, "tickets_completed": 0})
    for p in merged:
        weeks[week_start(parse_ts(p["merged_at"]), tz)]["prs_merged"] += 1
    for r in reviews:
        weeks[week_start(parse_ts(r["submitted_at"]), tz)]["reviews"] += 1
    for i in completed:
        weeks[week_start(parse_ts(i["completed_at"]), tz)]["tickets_completed"] += 1
    activity_by_week = [{"week_of": k, **v} for k, v in sorted(weeks.items())]

    churn = pr_churn(raw, bounds, tz)
    totals["pr_open_to_merge_hours"] = churn["open_to_merge"]["average_hours"]
    for stage in STAGES:
        totals[f"{stage}_hours"] = churn[stage]["average_hours"]

    estimates = estimate_rows(raw, config, bounds, tz)
    status_counts = defaultdict(int)
    for e in estimates:
        status_counts[e["status"]] += 1

    trend = None
    if previous:
        prev_totals = previous.get("totals", {})
        prev = {k: prev_totals.get(k, prev_totals.get(LEGACY_TOTALS.get(k))) for k in TREND_KEYS}
        trend = {
            "previous_period": previous.get("period"),
            "metrics": {
                k: {"current": totals[k], "previous": prev[k],
                    "delta": None if prev[k] is None or totals[k] is None else round(totals[k] - prev[k], 1)}
                for k in TREND_KEYS
            },
        }

    return {
        "period": raw["period"],
        "timezone": tz_name or "UTC",
        "gaps": raw.get("gaps", []),
        "totals": totals,
        "estimates": estimates,
        "estimate_summary": dict(sorted(status_counts.items())),
        "trend": trend,
        "cycle": cycle_outlook(raw, config, bounds, tz, estimates),
        "churn": churn,
        "charts": {
            "activity_by_week": activity_by_week,
            "activity_by_repo": activity_by_repo,
            "estimate_vs_actual": [
                {"ticket": e["ticket"], "expected_days": e["expected_days"], "actual_days": e["actual_days"]}
                for e in estimates if "expected_days" in e
            ],
        },
    }


def find_previous(runs_dir, before):
    """Most recent run that ended before `before`, by directory name <start>_<end>."""
    runs_dir = Path(runs_dir).expanduser()
    if not runs_dir.is_dir():
        return None
    best = None
    for d in runs_dir.iterdir():
        parts = d.name.split("_")
        if len(parts) != 2 or not (d / "metrics.json").is_file():
            continue
        try:
            end = date.fromisoformat(parts[1])
        except ValueError:
            continue
        if end < before and (best is None or end > best[0]):
            best = (end, d)
    return best[1] if best else None


def load_json(path):
    with open(Path(path).expanduser()) as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compute")
    c.add_argument("--raw", required=True)
    c.add_argument("--config", required=True)
    c.add_argument("--runs-dir", required=True)
    c.add_argument("--out", required=True)

    p = sub.add_parser("previous")
    p.add_argument("--runs-dir", required=True)
    p.add_argument("--before", required=True, help="YYYY-MM-DD; finds the latest run ending before this date")

    args = parser.parse_args(argv)

    if args.cmd == "previous":
        prev = find_previous(args.runs_dir, date.fromisoformat(args.before))
        if prev is None:
            print(json.dumps(None))
            return 0
        run = load_json(prev / "run.json") if (prev / "run.json").is_file() else {}
        start, end = prev.name.split("_")
        print(json.dumps({"dir": str(prev), "start": start, "end": end, "doc_url": run.get("doc_url")}))
        return 0

    raw = load_json(args.raw)
    config = load_json(args.config)
    for key in ("start", "end"):
        if not raw.get("period", {}).get(key):
            print(f"raw.json is missing period.{key}", file=sys.stderr)
            return 2
    prev_dir = find_previous(args.runs_dir, date.fromisoformat(raw["period"]["start"]))
    previous = load_json(prev_dir / "metrics.json") if prev_dir else None

    result = compute(raw, config, previous)
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    cycle = result["cycle"]
    print(json.dumps({"out": str(out), "totals": result["totals"], "estimate_summary": result["estimate_summary"],
                      "cycle": cycle and {k: cycle[k] for k in ("number", "mid_cycle", "load", "status")}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
