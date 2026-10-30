# Data shapes

Each role holds the same shape whatever platform it came from, so `metrics.py` and the doc never depend on the platform. PR covers merge requests too. All timestamps use ISO-8601. `metrics.py` accepts `Z` or an explicit offset. Unknown values are `null`; don't leave keys out.

## raw.json

```json
{
  "period": { "start": "2026-10-01", "end": "2026-10-14" },
  "platforms": { "code": "github", "tickets": "linear", "messages": "slack", "design": "figma" },
  "gaps": ["design: FIGMA_TOKEN not set"],
  "code": {
    "prs_authored": [
      {
        "repo": "acme/app", "number": 412, "title": "Add hall pass audit log",
        "url": "https://github.com/acme/app/pull/412",
        "state": "merged",
        "created_at": "...", "ready_at": "...", "first_commit_at": "...", "merged_at": "...",
        "additions": 220, "deletions": 40,
        "ticket_ids": ["ENG-123"]
      }
    ],
    "reviews": [
      {
        "repo": "acme/app", "number": 398, "title": "...", "url": "...",
        "author": "teammate", "state": "CHANGES_REQUESTED",
        "submitted_at": "...", "comment_count": 6
      }
    ],
    "comments": [
      { "repo": "acme/app", "number": 401, "url": "...", "created_at": "...", "body": "..." }
    ]
  },
  "tickets": {
    "issues": [
      {
        "identifier": "ENG-123", "title": "...", "url": "...",
        "estimate": 3, "status": "Done", "status_type": "completed",
        "in_progress_at": "...", "completed_at": "...",
        "project": "Hall Pass", "team": "ENG",
        "pr_urls": ["https://github.com/acme/app/pull/412"]
      }
    ],
    "comments": [
      { "issue": "ENG-130", "issue_title": "...", "url": "...", "created_at": "...", "body": "..." }
    ],
    "cycle": {
      "id": "uuid", "number": 42, "name": null, "team": "ENG",
      "starts_at": "...", "ends_at": "...",
      "issues": [
        {
          "identifier": "ENG-140", "title": "...", "url": "...",
          "estimate": 3, "status": "Code Review", "status_type": "started",
          "started_at": "...", "completed_at": null
        }
      ]
    }
  },
  "notes": {
    "file": "~/notes/1-1.rtf", "format": "rtf",
    "commands": [
      {
        "text": "I worked on the training repo, look at ~/repos/training",
        "kind": "source",
        "status": "done",
        "summary": "14 commits Oct 13–20: added a seeded demo school and a reset script",
        "sources": ["~/repos/training @ 3f2a9c1", "https://github.com/acme/training"]
      },
      { "text": "Lead with the Mailjet migration", "kind": "framing", "status": "done", "summary": null, "sources": [] }
    ]
  },
  "design": {
    "comments": [
      { "file_name": "...", "file_url": "...", "created_at": "...", "body": "...", "is_reply": false }
    ]
  },
  "messages": {
    "my_messages": 214,
    "conversations": [
      {
        "kind": "dm", "channel": "Sam Lee, Priya N.",
        "my_messages": 23, "first_at": "...", "last_at": "...",
        "permalink": "https://acme.slack.com/archives/D0.../p17...",
        "category": "mentoring",
        "summary": "Walked Sam through the referral permission model"
      },
      {
        "kind": "thread", "channel": "#behaviour-dev",
        "my_messages": 12, "first_at": "...", "last_at": "...",
        "permalink": "...", "category": "collaboration",
        "summary": "Worked out the incident type seeding plan with QA"
      }
    ],
    "skipped_for_data_rules": 0
  }
}
```

- `state` for a PR is one of `open`, `merged` or `closed` (closed without merging).
- `ready_at` is when the PR became ready for review. Use `created_at` if it was never a draft, and `null` if it's still a draft or unknown.
- `first_commit_at` is the author date of the PR's earliest commit that isn't also in one of the user's earlier PRs (stacked branches). `github_activity.py` fills it in for GitHub. Leave it `null` if it can't be found.
- `ticket_ids` are ticket keys found in the PR title or branch.
- Tickets never carry a `description`. `status_type` is one of `completed`, `canceled`, `started`, `unstarted`, `backlog` or `triage`. Each platform guide says how its states map onto these.
- `tickets.cycle` is the current cycle or sprint, or `null` when there isn't one or the platform has none. Its `issues` are every ticket assigned to the user in it, whatever their status.
- `notes` is `null` when no notes file was passed. `kind` is `source` (go and look at something) or `framing` (shapes the write-up). `status` is `done`, `skipped` or `failed`; for the last two, `summary` says why. `summary` paraphrases what was found. Command text is kept here and in `run.json` so the user can see what ran, but never goes into the doc.
- `messages.my_messages` counts all of the user's messages in the period, outside skipped channels. `conversations` lists DMs and group DMs (threads inside them included) at or above `messages.min_dm_messages` in config, and channel threads at or above `messages.min_messages`. `kind` is `dm` (including group DMs) or `thread`. `category` is one of `mentoring`, `learning`, `collaboration` or `other`. `summary` is a paraphrase, never a quote, and no message text appears anywhere in the file.

## highlights.json

```json
{
  "summary": "One or two sentences the user could say out loud to open the 1-1.",
  "talking_points": [
    {
      "headline": "Shipped hall pass audit logging two days ahead of estimate",
      "detail": "One to three sentences: what, why it mattered, the user's role.",
      "category": "shipped",
      "sources": ["https://github.com/acme/app/pull/412", "ENG-123"]
    }
  ],
  "appendix": {
    "shipped": [], "ahead_of_estimate": [], "reviews_and_guidance": [],
    "tooling_and_learning": [], "collaboration": [], "other": []
  },
  "blockers_asks": [ { "text": "...", "draft": true } ],
  "skipped_for_data_rules": 0
}
```

Each appendix entry looks like `{ "text": "...", "sources": ["..."] }`. The categories are defined in `rubric.md`.
