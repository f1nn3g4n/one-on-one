# Highlight rubric

The aim is to help the user **communicate** work they actually did. A manager should be able to follow every claim back to its source.

## Categories

| Category | What counts | Signals in the data |
|---|---|---|
| `shipped` | Work that merged or reached Done in the period | Merged PRs, completed tickets, especially those tied to a project or epic |
| `ahead_of_estimate` | Tickets with `status: "ahead"` in `metrics.estimates` | The ratio from metrics; quote the days, not just "fast" |
| `reviews_and_guidance` | Unblocking others, mentoring, setting direction | Reviews with `CHANGES_REQUESTED` or many comments, substantive review comments, design feedback, ticket comments that answer questions or propose approaches, conversations categorized `mentoring` |
| `tooling_and_learning` | Building, adopting or learning tools; growth | PRs touching CI, scripts, dev tooling or Claude skills; first PRs in a repo new to the user; conversations categorized `learning`; notes |
| `collaboration` | Cross-team or cross-functional work | Reviews or comments in repos outside the user's usual ones, design comments, tickets in other teams, conversations categorized `collaboration` |
| `other` | Anything real that fits nowhere else | |

## Choosing talking points (3–6)

Rank by how much the work mattered, not by how much activity it produced:

1. Items in the notes file the user passed, if any, and work that a notes command pointed at (a local repo, an extra org). Framing commands can reorder or drop points; follow them unless that would make a claim untrue.
2. Shipped work tied to a project or customer-visible feature.
3. Clear estimate wins (`ratio` ≤ 0.8) on tickets of 3+ points.
4. Guidance that changed someone else's outcome, such as a review that caught a bug or a comment that settled an approach.
5. Tooling or process improvements other people benefit from.

Merge related items into one point, for example a ticket, its PRs and its design thread. Five reviews on one PR count as one point. A conversation about a ticket or PR belongs with that work's point.

### Conversation talking points

Conversations from the messages platform get their own talking points. These sit alongside the 3–6 above rather than counting toward that limit:

- For each of `collaboration`, `learning` and `mentoring`, pick the conversation in that category with the most of the user's messages, and give it its own talking point. A category with no conversation gets no point and no placeholder.
- The headline says what the conversation achieved, not that it happened: "Worked through the referral and incident design with Luis", not "Talked with Luis a lot".
- The detail is the paraphrase plus how it connects to shipped work, if it does. The source is the permalink.
- If that conversation is also the main evidence for a work point (a design discussion behind a feature), mention it in one clause there and keep the full point here, so the same conversation isn't described twice.
- The other conversations go in the appendix under their category.
- Use the paraphrase, never message text. Name the other person only by the display name in `channel`. Only call a conversation mentoring when its category says so.

## Tone

- Specific and plain: "Reviewed 9 PRs across 4 repos, including requested changes that caught a missing permission check in #398". Avoid "was a strong collaborator".
- Use first person, since the user will be speaking these points.
- Never invent impact. If the data doesn't show why something mattered, describe what was done and leave the "why" for the user to add.
- Don't treat raw counts as wins on their own. Use them as supporting detail.

## Blockers / Asks (drafts)

Draft these only from evidence: tickets at `status: "over"`, PRs open more than 5 working days, a cycle at `status: "over"` (or `"under"`, framed as room to pick up more), a PR Churn stage that dominates open time (for example, over a working day on average to first review or from approval to merge, or PRs in `churn.open_prs` stuck in one stage), framed as a process question ("PRs waited 1.5 days on average for a first review; can we talk about review coverage?") and never about a named person, tickets with `past_estimate`, gaps in data, or anything in the notes. Phrase them as discussion prompts, for example "ENG-140 ran 2× over its estimate; worth talking through what made it harder than sized." Always mark them `draft: true`.
