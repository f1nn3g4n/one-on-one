# developer-summary

A Claude Code plugin marketplace. It currently holds one plugin.

## one-on-one

`/one-on-one:prep` gets you ready for a biweekly 1-1. It collects your activity for a date range and writes a Claude Doc you can share with your manager. The doc includes talking points, charts, output vs estimates, and how your current cycle or sprint is tracking.

The first run asks which platforms you use for each role and saves the answers:

| Role | Guided platforms | What's collected |
|---|---|---|
| Code | GitHub (`gh` CLI or connector), GitLab (`glab` CLI) | PRs/MRs you authored, reviews you gave, your PR comments |
| Tickets | Linear (connector), Jira (Atlassian connector or REST) | Your tickets' titles, estimates, status changes, links and your comments, plus every ticket you hold in the current cycle or sprint. **Never descriptions.** |
| Messages | Slack (connector), Microsoft Teams (Microsoft 365 connector) | Your own messages in DMs and threads, grouped into conversations, classified as mentoring, learning or collaboration, and paraphrased. Message text is never stored or quoted |
| Design | Figma (personal token) | Your comments on the files you name for that run |
| You | A notes file you pass on the command | Anything the tools miss, plus `claude:` commands that point at more sources |

GitHub, Linear, Slack and Figma have been tested end to end. The GitLab, Jira and Teams guides were written from those platforms' API docs and haven't been run yet; reports and fixes are welcome. Any other platform also works: the first run looks at the connector or CLI you have, proposes a collection plan for you to confirm, and saves it as a recipe in `~/.one-on-one/platforms/`. A feature the platform can't support (estimates need ticket status history, the cycle outlook needs sprints) is left out of the doc with the reason, never guessed at. Set a role to "None" to skip it.

**Data handling.** Ticket descriptions are never read. Comments on tickets matching `tickets.skip_comments` (for example customer-reported bugs) are never fetched, because comment tools return everyone's comments. Messages are limited to your own, found by an author-filtered search that returns no one else's text; if a platform can't do that, messages are skipped. Channels matching `messages.skip_channels` are skipped. Add your company's own rules (for example, never process customer or student records) to `sensitive_data.rules`, and a contact for data questions to `sensitive_data.contact`; the skill follows them on every run. Check your company's policy before pointing an AI tool at work systems.

### Install

**From a zip** (to share the plugin on its own):

```bash
scripts/package.sh
```

This builds `dist/one-on-one-<version>.zip` from the committed files, with `plugin.json` at the zip's root, and validates it. Commit your changes first, or the script refuses to run. Load the zip into a Claude Code session with:

```bash
claude --plugin-dir one-on-one-1.2.0.zip
```

`--plugin-dir` loads the plugin for that session only. The same zip works for plugin uploads that expect `.claude-plugin/plugin.json` at the root.

**As a marketplace** (persistent install, picks up updates):

```bash
claude plugin marketplace add <path-or-git-url-of-this-repo>
```

```bash
claude plugin install one-on-one@developer-summary
```

Bump `version` in `plugins/one-on-one/.claude-plugin/plugin.json` when you ship changes, so the zip name and `claude plugin update` both move with it.

### Set up

1. Connect what your platforms need: claude.ai connectors (connector settings) or MCP servers (`/mcp`), or install and log in to `gh` or `glab`. Each guide in `skills/prep/references/platforms/` lists its requirements.
2. For Figma: create a personal access token with `current_user:read`, `file_comments:read` and `file_content:read`, then make it available as `FIGMA_TOKEN`. On macOS you can keep it in the Keychain and load it in `~/.zshrc`:
   ```bash
   security add-generic-password -U -a "$USER" -s FIGMA_TOKEN -w
   ```
   ```bash
   echo 'export FIGMA_TOKEN="$(security find-generic-password -a "$USER" -s FIGMA_TOKEN -w)"' >> ~/.zshrc
   ```
   Restart Claude Code afterwards, because it only reads `FIGMA_TOKEN` when it starts. Each run asks which Figma files you commented on, so have their URLs handy.
3. Run `/one-on-one:prep`. On the first run it asks for your platforms, works out your identity in each, asks about anything it can't tell (orgs, workflow states, cycle team or board, exclusions, sizing guideline, data rules), and saves the answers to `~/.one-on-one/config.json`. Edit that file, or delete it to start over.

### Use

- `/one-on-one:prep` covers the period since your last run, or the last 14 days if there isn't one.
- `/one-on-one:prep 2026-10-01 to 2026-10-14` covers an explicit range.
- `/one-on-one:prep ~/notes/1-1.txt` adds your own notes. They rank first among talking points and get a "From my notes" section in the doc, which is left out when you don't pass a file. Plain text is expected, but `.md`, `.rtf` and `.docx` are converted. Start from `notes.template.txt` if you like. Each run keeps a copy of the notes it used.
- In the notes, a line starting with `claude:` is a command for that run rather than a note, for example `claude: I worked on the training repo, look at ~/repos/training` or `claude: Lead with the Mailjet migration`. Commands only read things and still follow the data rules. They're never copied into the doc, and the run lists any it skipped. The template explains the convention.

### Cycle outlook

The doc includes the current cycle (Linear) or sprint (Jira) for the team or board set in `tickets.cycle_team`: points completed, points still assigned to you, and whether the open work fits in the working days left. Open tickets are projected at their sized days scaled by your pace this period (the median of actual ÷ sized across measured tickets, or face value with fewer than 3), minus days already spent, so a run in the middle of a cycle shows whether you're likely to finish under, on track or over. When the period ends mid-cycle, the doc says the totals and trends are partway numbers that will still change.

Each run is saved under `~/.one-on-one/runs/<start>_<end>/`. The next run uses it for trends and to carry over follow-ups.

### PR Churn

The doc has a PR Churn section showing how long your merged PRs sat in each stage:
- **Draft:** from creating the PR to marking it ready for review.
- **Time to first review:** from ready to the first comment or review from someone other than you.
- **Time in review:** from that first review to the last approval.
- **Approval to merge:** from the last approval to the merge.

Each stage shows an average and a median, compared with last period. Only weekdays count. Bots and release merges are left out. A PR merged without a review or an approval is left out of the stages it never reached, and the doc says how many. Reviewers are never named. The section also lists open PRs with the stage each is in.

### How output vs estimates is measured

For each estimated ticket, the actual time starts at whichever came first: the ticket entering **In Progress**, or the first commit of a linked PR. Commits that also appear in your earlier PRs, such as the parent of a stacked branch, are ignored. It ends when the first linked PR was **ready for review**, and only weekdays count. Tracker integrations can move tickets to In Progress when the PR opens, often after the work started, so the first commit catches the earlier start. That's compared with `estimates.points_to_days` in your config:

- ≤ 0.8× expected is *ahead*.
- Over 1.2× is *over*.

Both thresholds are configurable.

### Layout

```
.claude-plugin/marketplace.json
scripts/package.sh           builds the plugin zip
plugins/one-on-one/
  .claude-plugin/plugin.json
  skills/prep/
    SKILL.md                 workflow
    references/              data schema, highlight rubric, doc template
    references/platforms/    one collection guide per platform, plus other.md for the rest
    scripts/metrics.py       deterministic counts, estimates, trends, chart rows
    scripts/github_activity.py
    scripts/figma_comments.py
    config.example.json
    notes.template.txt
    tests/                   unit tests (left out of the zip)
```

`metrics.py` uses only the standard library (Python 3.9+). To test it:

```bash
python3 -m unittest discover plugins/one-on-one/skills/prep/tests
```

## License

MIT. See [LICENSE](LICENSE).
