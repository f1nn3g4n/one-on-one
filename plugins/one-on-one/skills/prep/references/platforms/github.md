# GitHub (code)

Status: tested.

**Identity.** Run `gh api user --jq .login`, or use the GitHub connector's authenticated-user tool. Store the result as `code.user`. Ask which orgs to cover and store them as `code.orgs`.

**Collect.** If `gh` is installed and authenticated (`gh auth status`), use the script. It gets ready-for-review times from PR timelines, which the connector doesn't expose, and prints the `code` block of `raw.json`:

```
python3 SKILL_DIR/scripts/github_activity.py --config ~/.one-on-one/config.json --start <start> --end <end>
```

Otherwise use the GitHub connector, once for each org in `code.orgs`:
- **PRs authored:** search `is:pr author:<user> org:<org> updated:>=<start>`.
- **PRs reviewed:** search `is:pr reviewed-by:<user> -author:<user> org:<org> updated:>=<start>`. List each PR's reviews and keep only the user's, with state, `submitted_at` and inline comment count.
- **PRs commented on:** search `is:pr commenter:<user> org:<org> updated:>=<start>`. Keep only the user's own comments.
- **Ready-for-review time:**
  - If the PR was never a draft, use `created_at`.
  - Otherwise use the first `ready_for_review` event: `gh api repos/<owner>/<repo>/issues/<n>/timeline --paginate --jq '[.[] | select(.event=="ready_for_review") | .created_at] | first'`.
  - Without `gh`, leave it `null`. The ticket then shows as not measured.
- **First commit:** the earliest commit author date in the PR (`pulls/<n>/commits`). Skip commits that also appear in one of the user's earlier PRs, which happens with stacked branches.
- **Activity (for PR Churn):** for each authored PR, every commit (committer date), review (state, and whether it has a body) and comment, from `pulls/<n>/commits`, `pulls/<n>/reviews`, `pulls/<n>/comments` and `issues/<n>/comments`. Mark each as `author`, `other` or `bot` (a `type: "Bot"` user or a login ending in `[bot]`). Don't keep comment bodies or other people's logins.
- **Ticket links:** take ticket keys (`ABC-123`) from the PR title and branch name and store them in `ticket_ids`.

**States.** `state` is `merged`, `open` or `closed` (closed without merging). Review states pass through as GitHub reports them: `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`.
