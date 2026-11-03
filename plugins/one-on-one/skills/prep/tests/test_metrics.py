import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import metrics  # noqa: E402

UTC = timezone.utc
CONFIG = {"timezone": "UTC", "estimates": {"points_to_days": {"1": 0.5, "3": 2, "5": 3}}}


def raw():
    return {
        "period": {"start": "2026-10-01", "end": "2026-10-14"},
        "code": {
            "prs_authored": [
                {"repo": "acme/app", "number": 1, "title": "a", "url": "u1", "state": "merged",
                 "created_at": "2026-10-02T10:00:00Z", "ready_at": "2026-10-02T10:00:00Z",
                 "merged_at": "2026-10-03T10:00:00Z", "additions": 10, "deletions": 2, "ticket_ids": ["ENG-1"]},
                {"repo": "acme/api", "number": 2, "title": "b", "url": "u2", "state": "open",
                 "created_at": "2026-10-08T10:00:00Z", "ready_at": "2026-10-13T10:00:00Z",
                 "merged_at": None, "additions": 5, "deletions": 0, "ticket_ids": []},
                {"repo": "acme/app", "number": 0, "title": "old", "url": "u0", "state": "merged",
                 "created_at": "2026-09-20T10:00:00Z", "ready_at": "2026-09-20T10:00:00Z",
                 "merged_at": "2026-09-21T10:00:00Z", "additions": 1, "deletions": 1, "ticket_ids": []},
            ],
            "reviews": [
                {"repo": "acme/app", "number": 9, "url": "r9", "author": "t", "state": "APPROVED",
                 "submitted_at": "2026-10-06T10:00:00Z", "comment_count": 2},
                {"repo": "acme/app", "number": 9, "url": "r9", "author": "t", "state": "CHANGES_REQUESTED",
                 "submitted_at": "2026-10-05T10:00:00Z", "comment_count": 3},
            ],
            "comments": [{"repo": "acme/web", "number": 4, "url": "c4", "created_at": "2026-10-07T10:00:00Z", "body": "x"}],
        },
        "tickets": {
            "issues": [
                # Thu 10:00 → PR ready Fri 10:00: 1 working day vs 2 expected → ahead.
                {"identifier": "ENG-1", "title": "t1", "url": "l1", "estimate": 3, "status": "Done",
                 "status_type": "completed", "in_progress_at": "2026-10-01T10:00:00Z",
                 "completed_at": "2026-10-03T12:00:00Z", "pr_urls": []},
                # Fri 10:00 → Tue 10:00 over a weekend: 2 working days vs 0.5 → over.
                {"identifier": "ENG-2", "title": "t2", "url": "l2", "estimate": 1, "status": "In Review",
                 "status_type": "started", "in_progress_at": "2026-10-09T10:00:00Z",
                 "completed_at": None, "pr_urls": ["u2"]},
                {"identifier": "ENG-3", "title": "t3", "url": "l3", "estimate": 2, "status": "In Progress",
                 "status_type": "started", "in_progress_at": "2026-10-10T10:00:00Z",
                 "completed_at": None, "pr_urls": []},
            ],
            "comments": [{"issue": "ENG-9", "created_at": "2026-10-04T00:00:00Z", "body": "y"}],
        },
        "design": {"comments": [{"file_name": "f", "file_url": "fu", "created_at": "2026-10-15T00:00:00Z", "body": "late"}]},
        "messages": {
            "my_messages": 40,
            "conversations": [
                {"kind": "dm", "channel": "A", "my_messages": 12, "category": "mentoring",
                 "first_at": "2026-10-02T10:00:00Z", "last_at": "2026-10-09T10:00:00Z"},
                # Ends the day before the period starts; only in the results because of search padding.
                {"kind": "thread", "channel": "#eng", "my_messages": 10, "category": "learning",
                 "first_at": "2026-09-29T10:00:00Z", "last_at": "2026-09-30T10:00:00Z"},
                {"kind": "thread", "channel": "#eng", "my_messages": 15, "category": "mentoring",
                 "first_at": "2026-10-13T10:00:00Z", "last_at": "2026-10-14T23:00:00Z"},
            ],
        },
    }


class WorkingDays(unittest.TestCase):
    def test_skips_weekend(self):
        start = datetime(2026, 10, 9, 10, tzinfo=UTC)  # Friday
        end = datetime(2026, 10, 13, 10, tzinfo=UTC)  # Tuesday
        self.assertEqual(metrics.working_days_between(start, end, UTC), 2.0)

    def test_reversed_is_zero(self):
        a = datetime(2026, 10, 9, tzinfo=UTC)
        self.assertEqual(metrics.working_days_between(a, a, UTC), 0.0)


class Compute(unittest.TestCase):
    def setUp(self):
        self.result = metrics.compute(raw(), CONFIG, None)

    def test_totals_respect_period(self):
        t = self.result["totals"]
        self.assertEqual(t["prs_opened"], 2)
        self.assertEqual(t["prs_merged"], 1)
        self.assertEqual(t["reviews_given"], 1)
        self.assertEqual(t["review_submissions"], 2)
        self.assertEqual(t["review_comments"], 5)
        self.assertEqual(t["tickets_completed"], 1)
        self.assertEqual(t["points_completed"], 3)
        self.assertEqual(t["design_comments"], 0)
        self.assertEqual(t["repos_touched"], 3)
        self.assertEqual(t["messages_sent"], 40)
        self.assertEqual(t["conversations"], 2)
        self.assertEqual(t["conversations_by_category"], {"mentoring": 2})

    def test_release_merge_excluded_from_lines(self):
        r = raw()
        r["code"]["prs_authored"].append(
            {"repo": "acme/app", "number": 99, "title": "chore: merge release/7.25 into master", "url": "u99",
             "state": "merged", "created_at": "2026-10-10T10:00:00Z", "ready_at": "2026-10-10T10:00:00Z",
             "merged_at": "2026-10-11T10:00:00Z", "additions": 50000, "deletions": 20000, "ticket_ids": []})
        t = metrics.compute(r, CONFIG, None)["totals"]
        self.assertEqual((t["lines_added"], t["lines_removed"], t["release_merges"]), (10, 2, 1))
        self.assertEqual(t["prs_merged"], 2)

    def test_missing_messages_is_zero(self):
        r = raw()
        del r["messages"]
        t = metrics.compute(r, CONFIG, None)["totals"]
        self.assertEqual((t["messages_sent"], t["conversations"]), (0, 0))

    def test_estimates(self):
        rows = {r["ticket"]: r for r in self.result["estimates"]}
        self.assertEqual(rows["ENG-1"]["status"], "ahead")
        self.assertEqual(rows["ENG-1"]["actual_days"], 1.0)
        self.assertEqual(rows["ENG-2"]["status"], "over")
        self.assertEqual(rows["ENG-2"]["ratio"], 4.0)
        self.assertEqual(rows["ENG-3"]["status"], "no_ready_time")
        self.assertEqual(len(self.result["charts"]["estimate_vs_actual"]), 2)

    def test_unmapped_points(self):
        r = raw()
        r["tickets"]["issues"][0]["estimate"] = 13
        rows = {x["ticket"]: x for x in metrics.compute(r, CONFIG, None)["estimates"]}
        self.assertEqual(rows["ENG-1"]["status"], "unmapped")

    def test_weeks_cover_period(self):
        weeks = self.result["charts"]["activity_by_week"]
        self.assertEqual([w["week_of"] for w in weeks], ["2026-09-28", "2026-10-05", "2026-10-12"])
        self.assertEqual(sum(w["reviews"] for w in weeks), 2)

    def test_trend(self):
        prev = {"period": {"start": "2026-09-17", "end": "2026-09-30"}, "totals": {"prs_merged": 3}}
        trend = metrics.compute(raw(), CONFIG, prev)["trend"]["metrics"]
        self.assertEqual(trend["prs_merged"]["delta"], -2)
        self.assertIsNone(trend["reviews_given"]["delta"])

    def test_trend_reads_legacy_totals(self):
        prev = {"period": {"start": "2026-09-17", "end": "2026-09-30"}, "totals": {"linear_completed": 4}}
        trend = metrics.compute(raw(), CONFIG, prev)["trend"]["metrics"]
        self.assertEqual(trend["tickets_completed"]["delta"], -3)


class StartSignal(unittest.TestCase):
    def test_first_commit_before_in_progress_wins(self):
        r = raw()
        # In Progress flipped by the GitHub integration when PR #1 opened, but work began Wed.
        r["tickets"]["issues"][0]["in_progress_at"] = "2026-10-02T10:00:00Z"
        r["code"]["prs_authored"][0]["first_commit_at"] = "2026-09-30T10:00:00Z"
        row = {x["ticket"]: x for x in metrics.compute(r, CONFIG, None)["estimates"]}["ENG-1"]
        self.assertEqual(row["start_source"], "first_commit")
        self.assertEqual(row["actual_days"], 2.0)
        self.assertEqual(row["status"], "on_track")

    def test_in_progress_used_without_commits(self):
        row = {x["ticket"]: x for x in metrics.compute(raw(), CONFIG, None)["estimates"]}["ENG-1"]
        self.assertEqual(row["start_source"], "in_progress")


class StackedCommits(unittest.TestCase):
    def test_child_ignores_parent_commits(self):
        import github_activity
        parent = {"created_at": "2026-10-01T00:00:00Z",
                  "_commits": [("2026-09-30T10:00:00Z", "models")]}
        child = {"created_at": "2026-10-03T00:00:00Z",
                 "_commits": [("2026-09-30T10:00:00Z", "models"), ("2026-10-02T09:00:00Z", "service")]}
        github_activity.set_first_commits([child, parent])
        self.assertEqual(parent["first_commit_at"], "2026-09-30T10:00:00Z")
        self.assertEqual(child["first_commit_at"], "2026-10-02T09:00:00Z")
        self.assertNotIn("_commits", child)


class DefaultSizing(unittest.TestCase):
    def test_team_guideline_applies_without_config(self):
        r = raw()
        r["tickets"]["issues"][1]["estimate"] = 0
        rows = {x["ticket"]: x for x in metrics.compute(r, {"timezone": "UTC"}, None)["estimates"]}
        self.assertEqual(rows["ENG-1"]["expected_days"], 3)
        self.assertEqual(rows["ENG-2"]["expected_days"], 0.5)


def with_cycle(issues, starts="2026-10-05T00:00:00Z", ends="2026-10-19T00:00:00Z"):
    r = raw()
    r["tickets"]["cycle"] = {"id": "c1", "number": 42, "name": None, "team": "ENG",
                            "starts_at": starts, "ends_at": ends, "issues": issues}
    return r


class CycleOutlook(unittest.TestCase):
    # Only two tickets were measured this period, too few for a pace, so open work is at face value.
    ISSUES = [
        {"identifier": "ENG-1", "estimate": 3, "status_type": "completed"},
        # Started Tue Oct 14 (1 working day in), 2 days sized → 1 left.
        {"identifier": "ENG-3", "estimate": 3, "status_type": "started", "started_at": "2026-10-14T00:00:00Z"},
        {"identifier": "ENG-4", "estimate": 1, "status_type": "unstarted"},
        {"identifier": "ENG-5", "estimate": 5, "status_type": "canceled"},
        {"identifier": "ENG-6", "estimate": None, "status_type": "unstarted"},
    ]

    def test_mid_cycle_projection(self):
        c = metrics.compute(with_cycle(self.ISSUES), CONFIG, None)["cycle"]
        self.assertTrue(c["mid_cycle"])
        self.assertEqual((c["working_days_elapsed"], c["working_days_left"], c["working_days_total"]), (8, 2, 10))
        self.assertIsNone(c["pace"])
        self.assertEqual((c["points_completed"], c["points_open"], c["unestimated_open"]), (3, 4, 1))
        self.assertEqual(c["projected_days"], 1.5)
        self.assertEqual((c["load"], c["status"]), (0.75, "under"))

    def test_pace_is_median_so_one_outlier_doesnt_dominate(self):
        r = with_cycle([{"identifier": "ENG-10", "estimate": 1, "status_type": "unstarted"}])
        # A third measured ticket, right on estimate: Mon 10:00 → 22:00 is 0.5 days vs 0.5.
        r["tickets"]["issues"].append({"identifier": "ENG-9", "title": "t9", "url": "l9", "estimate": 1,
                                       "status_type": "started", "in_progress_at": "2026-10-05T10:00:00Z",
                                       "completed_at": None, "pr_urls": ["u9"]})
        r["code"]["prs_authored"].append({"repo": "acme/app", "number": 9, "title": "c", "url": "u9", "state": "open",
                                          "created_at": "2026-10-05T12:00:00Z", "ready_at": "2026-10-05T22:00:00Z",
                                          "merged_at": None, "additions": 1, "deletions": 0, "ticket_ids": []})
        # Ratios 0.5, 1.0 and 4.0: the mean of days would give 1.17, the median gives 1.0.
        self.assertEqual(metrics.compute(r, CONFIG, None)["cycle"]["pace"], 1.0)

    def test_overrun_ticket_flagged_not_hidden(self):
        issues = [{"identifier": "ENG-7", "estimate": 1, "status_type": "started", "started_at": "2026-10-06T00:00:00Z"}]
        c = metrics.compute(with_cycle(issues), CONFIG, None)["cycle"]
        self.assertTrue(c["remaining"][0]["past_estimate"])
        self.assertEqual(c["remaining"][0]["remaining_days"], 0)
        self.assertEqual(c["status"], "under")

    def test_over_when_more_work_than_days(self):
        issues = [{"identifier": f"ENG-{n}", "estimate": 5, "status_type": "unstarted"} for n in (10, 11)]
        self.assertEqual(metrics.compute(with_cycle(issues), CONFIG, None)["cycle"]["status"], "over")

    def test_in_review_is_not_remaining_work(self):
        issues = [
            {"identifier": "ENG-2", "estimate": 1, "status_type": "started", "started_at": "2026-10-09T10:00:00Z"},
            {"identifier": "ENG-8", "estimate": 3, "status": "Code Review", "status_type": "started",
             "started_at": "2026-10-06T00:00:00Z"},
        ]
        c = metrics.compute(with_cycle(issues), CONFIG, None)["cycle"]
        self.assertEqual((c["tickets_in_review"], c["points_in_review"]), (2, 4))
        self.assertEqual((c["remaining"], c["status"]), ([], "under"))

    def test_cycle_ended_within_period(self):
        c = metrics.compute(with_cycle(self.ISSUES[:1], "2026-09-28T00:00:00Z", "2026-10-12T00:00:00Z"),
                            CONFIG, None)["cycle"]
        self.assertFalse(c["mid_cycle"])
        self.assertEqual(c["status"], "ended")

    def test_no_cycle(self):
        self.assertIsNone(metrics.compute(raw(), CONFIG, None)["cycle"])


def ev(at, kind, by, state=None, has_text=None):
    return {"at": at, "kind": kind, "by": by, "state": state, "has_text": has_text}


def churn_raw():
    r = raw()
    r["code"]["prs_authored"] = [
        {"repo": "acme/app", "number": 20, "title": "feat", "url": "p20", "state": "merged",
         "created_at": "2026-10-05T09:00:00Z", "ready_at": "2026-10-05T09:00:00Z",
         "merged_at": "2026-10-07T16:00:00Z", "additions": 1, "deletions": 0, "ticket_ids": [],
         "activity": [
             ev("2026-10-05T09:00:00Z", "commit", "author"),
             ev("2026-10-05T09:05:00Z", "comment", "bot"),
             # Reviewer asks for changes a day after the push.
             ev("2026-10-06T09:00:00Z", "comment", "other", has_text=True),
             # The fix lands 6 hours later, which restarts the wait for review.
             ev("2026-10-06T15:00:00Z", "commit", "author"),
             # A bare approval ends the review wait without asking anything of the author.
             ev("2026-10-07T15:00:00Z", "review", "other", "APPROVED", False),
         ]},
        # Draft over the weekend; only time from Monday's ready counts.
        {"repo": "acme/app", "number": 21, "title": "draft", "url": "p21", "state": "open",
         "created_at": "2026-10-09T09:00:00Z", "ready_at": "2026-10-13T10:00:00Z",
         "merged_at": None, "additions": 1, "deletions": 0, "ticket_ids": [],
         "activity": [
             ev("2026-10-09T09:00:00Z", "commit", "author"),
             ev("2026-10-09T12:00:00Z", "comment", "other", has_text=True),
         ]},
        {"repo": "acme/app", "number": 22, "title": "Merge release/7.25 into main", "url": "p22", "state": "merged",
         "created_at": "2026-10-01T09:00:00Z", "ready_at": "2026-10-01T09:00:00Z",
         "merged_at": "2026-10-12T09:00:00Z", "additions": 1, "deletions": 0, "ticket_ids": [], "activity": []},
    ]
    return r


class PrChurn(unittest.TestCase):
    def setUp(self):
        self.m = metrics.compute(churn_raw(), CONFIG, None)
        self.c = self.m["churn"]

    def test_open_to_merge_skips_release_merges(self):
        self.assertEqual(self.c["open_to_merge"]["count"], 1)
        self.assertEqual(self.c["open_to_merge"]["average_hours"], 55.0)

    def test_review_wait_runs_from_latest_push(self):
        self.assertEqual(self.c["review_wait"]["count"], 2)
        self.assertEqual(self.c["review_wait"]["average_hours"], 24.0)

    def test_response_wait_ignores_bots_and_bare_approvals(self):
        self.assertEqual(self.c["review_response"]["count"], 1)
        self.assertEqual(self.c["review_response"]["average_hours"], 6.0)

    def test_draft_feedback_ignored_and_open_wait_reported(self):
        waiting = self.c["waiting_on_review"]
        self.assertEqual([w["number"] for w in waiting], [21])
        self.assertEqual(waiting[0]["waiting_hours"], 38.0)

    def test_per_pr_row_and_totals(self):
        row = self.c["prs"][0]
        self.assertEqual((row["number"], row["waiting_on_review_hours"], row["waiting_on_author_hours"],
                          row["review_rounds"]), (20, 48.0, 6.0, 2))
        self.assertEqual(self.m["totals"]["review_wait_hours"], 24.0)

    def test_weekend_excluded(self):
        r = churn_raw()
        pr = r["code"]["prs_authored"][0]
        # Ready Friday 17:00, first review Monday 09:00: 7 + 9 weekday hours.
        pr["ready_at"] = pr["created_at"] = "2026-10-09T17:00:00Z"
        pr["merged_at"] = "2026-10-12T10:00:00Z"
        pr["activity"] = [ev("2026-10-12T09:00:00Z", "review", "other", "APPROVED", False)]
        c = metrics.compute(r, CONFIG, None)["churn"]
        self.assertEqual(c["review_wait"]["average_hours"], 16.0)

    def test_no_activity_is_empty_not_error(self):
        c = metrics.compute(raw(), CONFIG, None)["churn"]
        self.assertEqual(c["review_wait"], {"count": 0, "average_hours": None, "median_hours": None, "max_hours": None})


class Previous(unittest.TestCase):
    def test_finds_latest_before(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ["2026-09-03_2026-09-16", "2026-09-17_2026-09-30", "2026-10-01_2026-10-14", "junk"]:
                (Path(d) / name).mkdir()
                (Path(d) / name / "metrics.json").write_text("{}")
            from datetime import date
            found = metrics.find_previous(d, date(2026, 10, 1))
            self.assertEqual(found.name, "2026-09-17_2026-09-30")

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "raw.json").write_text(json.dumps(raw()))
            (p / "config.json").write_text(json.dumps(CONFIG))
            rc = metrics.main(["compute", "--raw", str(p / "raw.json"), "--config", str(p / "config.json"),
                               "--runs-dir", str(p / "runs"), "--out", str(p / "out" / "metrics.json")])
            self.assertEqual(rc, 0)
            self.assertIn("charts", json.loads((p / "out" / "metrics.json").read_text()))


if __name__ == "__main__":
    unittest.main()
