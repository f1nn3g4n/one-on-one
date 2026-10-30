# Jira (tickets)

Status: written from Jira Cloud's REST API docs and not yet tested. Note anything that doesn't match in `gaps`, and fix this file.

Use the Atlassian connector (Jira search with JQL, get issue). The `acli` CLI or the REST API with an API token also works. Never request the `description` field, and never request `*all` fields.

**Identity.** The connector's current-user tool, or `GET /rest/api/3/myself`, gives `accountId` and `displayName`. Store them as `tickets.user_id` and `tickets.name`.

**Setup questions:**
- **Estimate field.** Story points live in a custom field whose ID varies by site ("Story Points" or "Story point estimate"). Find it with `GET /rest/api/3/field`, then ask the user to confirm it. Store the ID as `tickets.estimate_field`. Ask too whether their points follow the points-to-days guideline.
- **In Progress status name**, and which statuses mean "in review" (`tickets.review_states`).
- **Board for sprints.** Store its ID as `tickets.cycle_team_id` and its name as `tickets.cycle_team`.
- Projects and labels to exclude, and the `skip_comments` labels and title prefixes.

**Collect:**
- **Issues:** JQL `assignee = currentUser() AND updated >= "<start>"`, with `fields=summary,status,resolution,resolutiondate,labels,project,<estimate_field>,sprint` and `expand=changelog`.
  - `identifier` is the issue key and `title` is `summary`. `url` is `<site>/browse/<key>`.
  - `estimate` is the estimate field's value.
- **Status types**, from `status.statusCategory.key`:
  - `new` → `unstarted`
  - `indeterminate` → `started`
  - `done` → `completed`
  - A done issue whose resolution means it wasn't done ("Won't Do", "Duplicate", "Cannot Reproduce") → `canceled`.
- **Dates from the changelog:**
  - `in_progress_at`: the first change of `status` to the In Progress status.
  - `completed_at`: `resolutiondate`.
- **PR links:**
  - Jira's development panel isn't in the standard API, so linking relies on the code side: ticket keys in PR titles and branches (`ticket_ids`).
  - Also add remote links that point at PRs or MRs (`GET /rest/api/3/issue/<key>/remotelink`) to `pr_urls`.
- **Comments:**
  - `GET /rest/api/3/issue/<key>/comment` returns everyone's comments. Skip the call for issues matching `tickets.skip_comments`, then keep only comments whose `author.accountId` is the user's.
  - Standard JQL can't search by commenter, so comments on issues the user isn't assigned to aren't collected. Note it in `gaps`, and don't scan projects to find them.
  - Comment bodies are in Atlassian Document Format, so flatten them to plain text.
- **Current sprint:**
  - Use JQL `assignee = currentUser() AND sprint in openSprints()` with the same fields, plus the sprint's `startDate`/`endDate`. Read the dates from the sprint field or `GET /rest/agile/1.0/board/<board>/sprint?state=active`.
  - If the period ends after the active sprint closed, use the sprint that contains the period's end.
  - Write the result under `tickets.cycle`, using the sprint ID, name and dates. `number` is `null` unless the name holds one.
- Apply `tickets.exclude` before writing anything.
