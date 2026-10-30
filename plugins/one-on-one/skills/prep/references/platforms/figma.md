# Figma (design)

Status: tested.

**Setup.** A personal access token with `current_user:read`, `file_comments:read` and `file_content:read` scopes, stored as `FIGMA_TOKEN` (see the README). `python3 SKILL_DIR/scripts/figma_comments.py whoami` gives the user's ID, which goes in `design.user_id`.

**Collect.** Figma can't list a person's comments across files, and personal tokens may lack the scope to list team projects, so ask on every run. Use AskUserQuestion, with options to paste URLs (in Other) or skip: "Which Figma files did you comment on between <start> and <end>? Paste their URLs." Don't save the URLs, because the files change from period to period. Then run:

```
python3 SKILL_DIR/scripts/figma_comments.py comments --config ~/.one-on-one/config.json --start <start> --end <end> --file <url> [--file <url> ...]
```

Its output goes in `raw.json` as `design.comments`. If the user skips, or `FIGMA_TOKEN` is unset, record a gap.
