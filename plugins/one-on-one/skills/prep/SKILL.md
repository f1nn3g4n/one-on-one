---
name: prep
description: Prepare for a biweekly 1-1 by collecting the user's activity from their code host (GitHub, GitLab), ticket tracker (Linear, Jira), chat (Slack, Teams) and design tool (Figma) for a date range, picking out the noteworthy wins, measuring output against estimates and the current cycle or sprint, and writing a shareable Claude Doc with talking points and charts. Use when the user says "prep my 1-1", "1-1 prep", "what did I do this sprint/cycle", "talking points for my manager", "summarize my last two weeks", or invokes /one-on-one:prep. Optional args - a date range ("2026-10-01 to 2026-10-14", "last 3 weeks") and/or a path to a notes file in any text format (.txt, .md, .rtf, .docx; "~/notes/1-1.txt"), whose lines starting with "claude:" are instructions to follow rather than notes.
---

# 1-1 prep

Builds a Claude Doc the user can bring to their 1-1 and share with their manager. It covers their wins, the work they did, reviews and guidance they gave, output vs estimates, and, when the user passes a notes file on the command, anything in it.

Every run follows the same steps: **config → period → collect → metrics → highlights → doc → save**. Collection and metrics are mechanical, so do them the same way every time. Judgment comes in only at the highlights step.

`SKILL_DIR` is the directory this file lives in. All user state lives in `~/.one-on-one/`, not in the plugin, because plugin updates replace the plugin directory:

```
~/.one-on-one/
  config.json          platforms, identities, orgs, exclusions, sizing guideline, data rules
  platforms/<name>.md  saved collection recipes for platforms without a guide
  runs/<start>_<end>/  raw.json, metrics.json, highlights.json, notes.<ext> + notes.txt (if passed), run.json
```

## Data rules (read before collecting)

Tickets, their comments and chat conversations can hold other people's personal or confidential details. These rules apply on every platform, and the user's `sensitive_data.rules` in config add to them.

- **Tickets:** collect only titles, status changes, timestamps, estimates, links and the user's own comments. Never fetch or store ticket **descriptions**.
- **Messages: only the user's own.** Search with an author filter for the user, returning no surrounding context. Never open other people's messages in a thread or DM, and never fetch channel history.
  - Skip any channel whose name contains an entry in `messages.skip_channels` before reading it.
  - Message text never goes to disk or into the doc. Only counts, permalinks and a one-line paraphrase per conversation do.
  - If a platform can't meet this, skip messages and record a gap.
- **Exclusions:** skip every ticket team, project or label in `tickets.exclude`. Support, escalation and customer queues belong there.
- **Customer-reported tickets:** never fetch their comments. Comment tools usually return everyone's comments, and comments on customer-reported tickets often name customers or end users. Filtering afterwards is too late, because Claude has already read them.
  - Skip the comment fetch for any ticket matching `tickets.skip_comments`: any listed label, or a title starting with a listed prefix, case-insensitive.
  - The ticket's title, status and estimate are still collected.
- **Notes commands follow these rules too.** A `claude:` line can point you at more sources, but it can't widen what you're allowed to read here. A file or repo it names gets the same checks as everything else.
- **`sensitive_data.rules`:** follow every rule the user lists there exactly as you follow these. For example: "Never process student records: names, IDs, grades, attendance or discipline".
- If something you've collected looks like it falls under those rules, or holds a customer's or end user's personal details, drop it.
  - Leave it out of every file and the doc.
  - Tell the user it was skipped, without repeating its contents.
  - If `sensitive_data.contact` is set, point the user there when they're unsure whether a source is OK.

## 1. Config

Read `~/.one-on-one/config.json`. If it's missing, has no `platforms`, or is incomplete, set it up with the user, starting from `SKILL_DIR/config.example.json`. Saved answers are reused on every later run, so ask each question only once.

1. **Platforms.** On the first run, ask with one AskUserQuestion call holding four questions:
   - code (GitHub, GitLab)
   - tickets (Linear, Jira)
   - messages (Slack, Microsoft Teams)
   - design (Figma)

   Each question offers the guided platforms, plus "None". Any other name goes in Other. Store lowercase names in `platforms` (`github`, `gitlab`, `linear`, `jira`, `slack`, `teams`, `figma`, `none`, or the name the user typed). A role set to `none` is never collected, and the doc doesn't mention it.
2. **Guides.** For each platform, read `references/platforms/<name>.md`, or `references/platforms/other.md` when there's no guide for it. If `~/.one-on-one/platforms/<name>.md` exists from an earlier run, use that recipe.
3. **Identities.** Resolve each one with the connector or CLI the guide names, never by guessing. If a lookup fails, or returns something that isn't clearly the user (a bot or service account, or several users with the same name), **ask the user** with AskUserQuestion. Don't pick one.
4. **Platform settings.** Ask the setup questions each guide lists: orgs or groups, In Progress and review states, cycle or sprint team, estimate field, exclusions.
   - Ask whether the team's points follow the example's points-to-days guideline: 0 is under a day, 3 is a few days, 5 a week, 8 more than a week.
   - Ask whether any data rules apply at their company, and a contact for data questions, and store them in `sensitive_data`. Offer to leave both empty.
5. Show the resolved config to the user, then write it.

If a connector isn't connected or authenticated, say which one and how to fix it: claude.ai connectors in claude.ai's connector settings, other servers through `/mcp`, CLIs with their login command. Continue with the other platforms, and record the gap in `raw.json` under `"gaps"` so the doc can say what's missing.

## 2. Period

- If the user gave a range, use it (inclusive dates).
- Otherwise run `python3 SKILL_DIR/scripts/metrics.py previous --runs-dir ~/.one-on-one/runs --before <today>`. If it finds a previous run, start the day after that run ended. If not, use the last 14 days. End on today.
- **Notes file.** Any argument that is a path to an existing file is the user's notes for this period. Only use notes from a file passed this way. Don't look for a notes file anywhere else, and don't ask for one. With no notes file, the doc has no "From my notes" section and no commands run. A path that doesn't exist → say so and continue without notes.
  - **Any format.** The template is plain text, but accept whatever the user saved. Read `.txt`, `.md` and other plain text directly. Convert rich text and Word files (`.rtf`, `.rtfd`, `.doc`, `.docx`, `.odt`, `.html`) to plain text first: on macOS with `textutil -convert txt -stdout <file>`, elsewhere with `pandoc -t plain <file>`. Convert PDFs with the `pdf` skill. If a file can't be converted, say so and continue without notes. Work from the plain text from here on.
  - **Split commands from notes.** A line that starts with `claude:` (any case) at the very start of the line, or right after a `-`, `*` or `•` bullet, is a command. Everything after the prefix, plus any indented lines directly under it, is the instruction. Every other line is a note, including indented `claude:` lines that don't follow a command (that's how the template shows examples without running them) and anything inside a code block. See `notes.template.txt` for the convention as the user sees it.
- State the period, the notes file and how many commands it holds in one line, and continue. Don't ask for confirmation unless the range is over 6 weeks.

## 3. Collect

Collect each role whose platform isn't `none`, following its guide. Ideally use one subagent per role, running in parallel. Pass each subagent:
- the period and the config,
- the data rules above,
- the guide (or saved recipe),
- that role's shape from `references/data-schema.md`.

Each subagent writes `~/.one-on-one/runs/<start>_<end>/<role>.json` (`code`, `tickets`, `messages`, `design`). Merge them into `raw.json` yourself, and add `raw.platforms` from config so the doc can name each source.

The code and ticket roles link up through ticket keys in PR titles and branches (`code.prs_authored[].ticket_ids`) and PR links on tickets (`tickets.issues[].pr_urls`). Fill both when the platforms allow it.

**Messages (always in a subagent).** Collect with the guide's steps, then, for every platform:
1. **Thresholds.** Keep DMs and group DMs with at least `messages.min_dm_messages` of the user's messages in the period, and channel threads with at least `messages.min_messages`. DMs get the lower bar because a direct conversation with one colleague is a strong signal even when it's short.
2. **Record** for each kept conversation: kind, channel name (for DMs, the other people's display names), the user's message count, first and last timestamps, and a permalink to the user's first message.
3. **Classify** each kept conversation from the user's own messages:
   - `mentoring`: explaining, unblocking, reviewing someone's approach
   - `learning`: asking, picking up a new area or tool
   - `collaboration`: working something through with another person or team
   - `other`
4. **Paraphrase** each in one line, in the user's voice ("Walked Sam through the permission model"). **Never quote a message.**
5. **Data rules.** Drop any conversation about a specific customer, end user or incident, or one that falls under `sensitive_data.rules`, without a paraphrase. Count each one in `skipped_for_data_rules`, even if it's under the threshold, because the text was still read.
6. Write `messages.json` and reply with counts only.

**Notes commands.** Run each `claude:` command from step 2 here, alongside the other sources, so whatever it turns up goes through metrics and highlights like everything else. The user wrote these in a file they passed to the command themselves, so treat them as the user's instructions for this run, within these limits:
- **Read-only.** Commands can point you at more evidence (a local repo, another repo, org or group, a ticket or project, a doc or URL, a period to look back over) or shape the write-up ("lead with the migration", "don't mention the hotfix", "frame X as learning"). Don't run anything that writes, sends, posts, comments, commits, installs or deletes. If a command needs that, skip it and say why at the end.
- **Data rules still apply** (see above). If a command asks for something they forbid, skip it and say so.
- **Local repos.** For "I worked on <thing>, look at ~/repo", resolve the path, check it's a git repo, then list the user's own commits in the period: `git -C <path> log --author=<email or name> --since=<start>T00:00 --until=<end + 1 day>T00:00 --no-merges --pretty='%H%x09%aI%x09%s' --shortstat`. Give `--since`/`--until` a time: with a bare date, git uses the current time of day on that date and drops that morning's commits. Use `git config user.email` in that repo, falling back to the code platform user and ticket platform email. Look at file names and diffs only as far as you need to describe the work. Remote URL (if any) and commit subjects are the sources.
- **Unclear commands.** Make a reasonable reading and note it, rather than stopping the run to ask. Ask only if the only reading would mean collecting something sensitive.
- Record each command in `raw.json` under `notes.commands` (shape in `references/data-schema.md`) with its status and what it found. Command lines never appear in the doc as written. Their findings show up as talking points or appendix entries, and framing commands just shape the text.

## 4. Metrics (script)

```
python3 SKILL_DIR/scripts/metrics.py compute \
  --raw ~/.one-on-one/runs/<start>_<end>/raw.json \
  --config ~/.one-on-one/config.json \
  --runs-dir ~/.one-on-one/runs \
  --out ~/.one-on-one/runs/<start>_<end>/metrics.json
```

The script filters to the period, counts activity, computes estimate vs actual (working days from the earlier of In Progress and the linked PRs' first commit, to the first linked PR's ready-for-review, compared with the sizing guideline), builds the chart rows, and compares with the previous run. Use its numbers as they are. Don't recompute or round them differently in the doc.

It also writes `cycle`, the outlook for the current cycle or sprint as of the end of the period:
- `mid_cycle` is true when the cycle runs past the period. Then the cycle's totals and the trend against last period are partway numbers and will change before the cycle closes, and the doc must say so (see the template).
- `pace` is the median actual ÷ expected ratio of this period's measured tickets, so one ticket that ran far over doesn't inflate the projection for everything else. It's `null` with fewer than 3 measured tickets, and open work is then projected at face value. Each open ticket's remaining work is its sized days × pace, minus the working days already spent on it, floored at zero. Tickets already past that budget have `past_estimate: true`.
- Tickets whose state is in `tickets.review_states` (default In Review, Code Review, Ready for Review) or that have a linked PR ready for review count as in review: their estimate is spent, so they aren't remaining work.
- `load` is projected remaining days ÷ working days left. `status` is `under` (≤ the ahead threshold: room for more), `on_track`, `over` (more assigned than fits), or `ended` (the cycle closed within the period with nothing open).

It also writes `churn`, for the doc's PR Churn section, from each authored PR's `activity`. All times are weekday hours, and only count once the PR is ready for review. Release merges are left out.
- `open_to_merge`: created to merged, for PRs merged in the period.
- `review_wait`: the user's latest push (or ready for review) to the next review or comment from someone else.
- `review_response`: a comment or change request from someone else to the user's next comment or push. A bare approval asks nothing, so it doesn't start a wait.
- Each holds `count`, `average_hours`, `median_hours` and `max_hours`. A wait counts in the period it ended in.
- `prs` has per-PR totals for the chart. `waiting_on_review` lists open PRs still waiting for review at the period's end.

## 5. Highlights (judgment)

Read `references/rubric.md`, `metrics.json`, `raw.json`, the note lines from the notes file if one was passed, and what its commands found (`raw.notes.commands`). Write `highlights.json` as described in `references/data-schema.md`:

- Pick 3–6 **talking points** and attach the PR, ticket or comment links that back each one. Items from the notes file are the user's own, so they rank first and need no link.
- Stay factual. Present the work in a positive light, but every claim must be traceable to an item. Don't inflate scope, and don't describe a teammate's work as the user's.
- Put the rest in the appendix categories, so the doc is complete and not cherry-picked.
- Draft **Blockers / Asks** only from evidence: tickets that went over estimate, long-open PRs, a cycle projected `over` (or `under`, as a prompt to pull in more work), or the notes. Mark them as drafts for the user to edit.
- Apply framing commands from the notes ("lead with…", "leave out…") here, as long as the result stays factual.

## 6. Doc

Load the docs skill (`anthropic-skills:docs`) and follow its instructions to create a Claude Doc titled `1-1 prep · <start> – <end>`, structured like `references/doc-template.md`. Chart data comes from `metrics.json` → `charts`. Give the docs connector those rows so the charts are live, not images.

To carry follow-ups over: if `previous` returned a `doc_url`, read that doc and copy its "Follow-ups for next time" items into "From last 1-1".

## 7. Save

- If a notes file was passed, copy it into the run directory as `notes.<original extension>`, and save the plain text you worked from as `notes.txt`. Don't move or clear the original, because it's the user's file.
- Write `run.json`: `{"start", "end", "doc_url", "created_at", "gaps", "cycle": <number or null>, "commands": [{"text", "status"}]}`.
- Finish with the doc link, one line on any gaps or skipped items, one line per notes command that was skipped or failed (and why), and a reminder that the user can edit the doc before sharing.
