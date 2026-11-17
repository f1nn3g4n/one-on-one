# Doc template

Title: `1-1 prep · <start> – <end>`. Under the title: the date and a mention of the user.

Use the sections below in this order. Leave out a section only if it has nothing in it, except "Blockers / Asks" and "Follow-ups for next time", which always appear so the user can fill them in during the meeting.

1. **TL;DR**: `highlights.summary`. When `metrics.cycle.mid_cycle` is true, end with one short sentence naming the cycle and how far through it the period ends, e.g. "Cycle 42 is 8 of 10 working days in, so these numbers will still move."
2. **By the numbers**: one lead sentence with the headline totals, then a two-column table (measure · this period) from `metrics.totals`: PRs merged, PRs opened, PRs reviewed (with review submissions), tickets completed (with points), lines changed in merged PRs, repos touched, and design comments when collected. Message counts don't go here: conversations show up through their talking points. Use the platform's own words where they differ (merge requests on GitLab, sprints on Jira). When `metrics.trend` exists, add a "Last period" column and a "Change" column. Draw charts here only when they have enough points to show a shape:
   - `charts.activity_by_week` as a grouped bar chart only when the period spans 5 or more weeks. A two-week period gives 2–3 bars per series, which a table shows better.
   - `charts.activity_by_repo` as a horizontal bar chart only when there are 5 or more repos. Otherwise "Repos touched" in the table covers it.
   - When `metrics.cycle.mid_cycle` is true, put a callout under the table: the period ends mid-cycle, so the totals and the change from last period cover part of a cycle and are subject to change. Don't call a drop in the "Change" column a decline when it's explained by the partial cycle.
3. **Talking points**: one subheading per talking point, with the detail and source links.
4. **Output vs estimates**: a dot plot of actual ÷ estimated working days per ticket from `charts.estimate_vs_actual`, sorted by ratio. Mark the on-track band (the configured thresholds) and a 1× reference line, highlight only the tickets that ran over, and put "actual d vs estimated d" labels in a column to the right. Don't add a table of the same numbers: the chart's hover and labels carry them. Under the chart, add one line on how actuals are measured: from the earlier of In Progress and the first commit to the first linked PR being ready for review, weekends excluded (tracker integrations can set In Progress when a PR opens, which is often after work starts). List tickets with `status: "no_ready_time"` or `"unmapped"` separately with the reason.
5. **PR Churn**: only when `metrics.churn.open_to_merge.count` is above 0, or `churn.open_prs` isn't empty.
   - **Lead sentence:** the average time open to merged, and the stage that took longest on average. For example: "My PRs took 2.6 days from opening to merge; most of that was waiting 1.2 days for a first review."
   - **Table:** Stage · Average · Median · PRs, with a "Last period" column when `metrics.trend` has the matching `_hours` key. The rows, in order:
     - Draft: created to ready for review
     - Time to first review: ready to the first comment or review from someone other than me (bots don't count)
     - Time in review: first review to the last approval
     - Approval to merge: last approval to merged
   - **Skipped PRs:** if `churn.skipped` counts any merged PRs with no review or no approval, say so in one line under the table. Those PRs are left out of the stages they never reached.
   - **Units:** show under 48 hours in hours, otherwise in days (hours ÷ 24, one decimal). Say once that only weekdays count.
   - **Chart:** when `churn.prs` has 5 or more PRs, draw a horizontal stacked bar per PR, longest first, with one segment per stage in the order above.
     - Use shades of one hue, light to dark, so the order of stages reads.
     - Label the segments in a legend.
     - Leave out a stage that's `null`.
     - With fewer PRs, leave the chart out; the table covers it.
   - **Still open:** list `churn.open_prs` with the stage each is in and how long it has been there, longest first.
   - **Never name reviewers** or imply who was slow. This is about how long work sits in each stage, not about people.
6. **Cycle outlook**: only when `metrics.cycle` exists. One lead sentence: cycle number and dates, working days elapsed of total, points completed and points still open, and how many of those open are already in review. Then the projection in plain words from `status` and `load`, e.g. "At this period's pace (1.2× sizing), the 4 open points need about 2 working days, with 2 left: on track." Say *under* as room to take on more, and *over* as more assigned than fits. Then a short table of `cycle.remaining` (ticket, points, days worked, days left), marking `past_estimate` rows. Mention `unestimated_open` tickets by count, since they aren't projected. When `mid_cycle` is false, describe the cycle as finished and drop the projection. Under it, one line on the method: open tickets' sized days × this period's pace (the median of its tickets' actual ÷ estimate, or face value with fewer than 3), less days already spent, against the working days left. When `pace` is `null`, say "at face value" in place of the pace.
7. **From my notes**: only when the user passed a notes file to the command. Its note lines, lightly tidied; never the `claude:` command lines. With no notes file, or a file holding only commands, leave this section out entirely, with no placeholder.
8. **From last 1-1**: follow-ups carried over from the previous doc, or leave this section out on the first run.
9. **Blockers / Asks**: the drafts, each marked *(draft)*.
10. **Follow-ups for next time**: empty bullets for the meeting.
11. **Appendix: all activity**: the `highlights.appendix` categories as bullet lists (conversations appear under their category as the paraphrase plus a permalink, never a quote), then a "Data sources" line listing what was collected from which platform (including what notes commands added, described by what was looked at, such as "local commits in ~/repos/training"), any `gaps`, and how many items were skipped under the data rules (count only).
