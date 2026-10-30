# Linear (tickets)

Status: tested.

**Identity.** Call `get_user` with `"me"`, and store `id` and `name` as `tickets.user_id` and `tickets.name`.

**Setup questions:**
- The workflow state that means In Progress. The default is the first state of type `started`.
- Teams, projects or labels to exclude.
- `skip_comments` labels and title prefixes.
- The cycle team. Resolve it with `list_teams` and store its key and UUID as `tickets.cycle_team` and `tickets.cycle_team_id`, because `list_cycles` only accepts the UUID. If the user is on several teams, suggest the one with most of their recent tickets.

**Collect:**
- **Issues:** `list_issues` with `assignee: "me"` and `updatedAt: <start>`. Pass `fields` explicitly and **leave out `description`**: `id, title, url, estimate, status, statusType, startedAt, completedAt, project, team, labels, cycleId`.
  - `id` returns the identifier (`ABC-123`), so store it as `identifier`.
  - `estimate` comes back as `{value, name}`, so store `value`.
  - `statusType` maps straight onto `status_type`.
- **History and PR links:** for each issue with an estimate, call `get_issue` with `fields: ["stateHistory", "attachments"]`.
  - `in_progress_at` is the first time the issue entered the In Progress state.
  - Attachment URLs that point at PRs or MRs go in `pr_urls`.
- **Comments:** call `list_comments` on those issues, **except ones matching `tickets.skip_comments`**. Keep only comments the user wrote.
  - `list_comments` returns everyone's comments, so the skip has to happen before the call.
  - Record in `gaps` how many tickets were skipped this way.
  - The connector can't search by commenter, so comments on tickets the user isn't assigned to aren't collected. Note this in `gaps`.
- **Current cycle:**
  - Call `list_cycles` with `teamId: tickets.cycle_team_id` and `type: "current"`. If the period ends before that cycle starts, call it without `type` and pick the cycle containing the period's end.
  - Then call `list_issues` with `assignee: "me"`, `cycle: <cycle id>`, `includeArchived: false` and the same fields, following every page.
  - Write the result under `tickets.cycle`, using `startsAt`/`endsAt` and each issue's `status` (state name) and `startedAt`.
- Apply `tickets.exclude` before writing anything.
