# GitLab (code)

Status: written from GitLab's API docs and not yet tested. Note anything that doesn't match in `gaps`, and fix this file.

Use the `glab` CLI if it's installed and authenticated (`glab auth status`). Its `glab api` command calls the REST API, and paths below are relative to `/api/v4`. A GitLab connector also works if it exposes the same data. Self-managed instances work the same way through `glab` with `GITLAB_HOST`.

**Identity.** `glab api user` returns `username` and `id`. Store `username` as `code.user` and `id` as `code.user_id`. Ask which groups to cover and store their full paths as `code.orgs`.

**Collect.** Page with `--paginate`, and pad the dates by a day on each side as the GitHub script does.
- **MRs authored:** `groups/<group>/merge_requests?author_username=<user>&updated_after=<start>&scope=all`, once per group.
- **Reviews and comments:** `users/<user_id>/events?after=<start - 1 day>&before=<end + 1 day>`.
  - `action_name: "approved"` on a merge request is a review with state `APPROVED`.
  - A `commented on` event with `note.noteable_type: "MergeRequest"` is a comment. Diff notes on someone else's MR count toward that MR's review `comment_count`. Merge several diff notes on the same MR on the same day into one `COMMENTED` review.
  - Newer GitLab versions record "requested changes" as a reviewer state. Use `projects/<id>/merge_requests/<iid>/reviewers` where it's available, and map it to `CHANGES_REQUESTED`.
- **For each authored MR:**
  - `state`: `merged`, `opened` (store as `open`) or `closed`.
  - **Ready-for-review time:**
    - If the MR was never a draft, use `created_at`.
    - Otherwise use the first system note saying it was "marked this merge request as **ready**", from `projects/<id>/merge_requests/<iid>/notes?sort=asc`. Read only notes where `system: true`, so no one's comments are loaded.
  - **First commit:** the earliest `authored_date` from `projects/<id>/merge_requests/<iid>/commits`, with the same stacked-branch exclusion as GitHub.
  - **Lines:** `projects/<id>/merge_requests/<iid>/diffs`. Count `+` and `-` lines in each `diff`, not the `+++` and `---` headers. If that's too heavy, leave `additions`/`deletions` `null` and record a gap.
  - **`ticket_ids`:** ticket keys from the title and `source_branch`.
  - **`activity` (for PR Churn):**
    - Commits: `committed_date` from the commits call.
    - Comments: non-system notes from `projects/<id>/merge_requests/<iid>/notes`. Read only each note's `author` and `created_at`; don't keep the body.
    - Reviews: approvals from the MR's `approved` system notes, with state `APPROVED`. "Requested changes" system notes map to `CHANGES_REQUESTED`.
    - Mark each event `author`, `other` or `bot` (`author.bot` is true, or the username ends in `_bot`).
- `repo` is `path_with_namespace`, `number` is `iid`, and `url` is `web_url`.
