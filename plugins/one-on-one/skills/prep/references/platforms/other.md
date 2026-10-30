# Any other platform

For a platform without its own guide here. This works only as well as the connector or CLI you can reach. Say so in the doc's data sources line, and don't fill gaps by guessing.

## First run: work out a recipe

1. **Find a way in.**
   - Look for a connector: search your tools for the platform's name.
   - Otherwise look for an installed CLI that is already authenticated.
   - If neither exists, tell the user what's needed (a connector to authorize, or a CLI to install and log in) and record a gap.
   - Never ask for passwords or tokens in chat.
2. **Map what you can reach onto the role's shape** in `data-schema.md`. Then check each capability below.
3. **Confirm before collecting.** Show the user, in a few lines, the plan:
   - which tools you'll call,
   - which fields map where,
   - which features this platform can and can't support.

   Ask them to confirm.
4. **Save the recipe** to `~/.one-on-one/platforms/<platform>.md`, in the same form as the guides here. Use it on later runs, so collection stays the same from run to run. If it stops working, fix it and tell the user what changed.

## Capabilities

A feature that needs a missing capability is left out of the doc, with the reason in `gaps`. It is never estimated by other means.

| Role | Capability | Needed for |
| --- | --- | --- |
| code | Your PRs/MRs with created, merged, and (for drafts) ready-for-review times | Counts, estimates |
| code | Commit author dates per PR | Earlier start signal for estimates |
| code | Reviews you gave, with state | Reviews in the doc |
| tickets | Your assigned tickets with title, status category, estimate, completed time | Counts, points |
| tickets | Status change history | Output vs estimates |
| tickets | Current sprint or cycle with dates and its tickets | Cycle outlook |
| tickets | Comments filtered to their author, or a per-ticket fetch you can skip | Your ticket comments |
| messages | Search limited to messages **you** wrote, returning no one else's text | Anything from messages |
| design | Your comments on a file, with dates | Design comments |

## Hard limits

- **Messages:** if the platform can't return only the user's own messages without loading other people's, skip messages entirely. Don't read conversations and filter afterwards.
- **Tickets:** never request description or body fields. If the tool always returns them, use it only for the IDs you need and don't keep or reason about the description.
- **Every role:** apply `sensitive_data.rules` and the data rules in `SKILL.md` exactly as you would on a platform with a guide.
