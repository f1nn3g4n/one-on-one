# Slack (messages)

Status: tested.

Always run this in a subagent. It keeps message text out of the main context and off disk.

**Identity.** Use the connector's auth or current-user tool, and store the `U…` ID as `messages.user_id`.

**Collect (in the subagent):**
1. Search the user's own messages: `from:<@user_id> after:<start - 1 day> before:<end + 1 day>`, following every page.
   - Set **`include_context: false`**, because the default returns other people's surrounding messages.
   - Never call thread-read or channel-read tools.
   - Drop results from channels matching `messages.skip_channels` without reading them further.
2. Group the messages by conversation.
   - A DM or group DM is one conversation, including any threads inside it, and its `kind` is `dm`.
   - A thread in a channel is grouped by channel plus thread timestamp, and its `kind` is `thread`.
   - A message posted in a channel outside any thread belongs to no conversation and is only counted.
3. Apply the thresholds and classification in `SKILL.md`, step 3. The permalink is the one search returns for the user's first message in the conversation. For DMs, `channel` is the other people's display names.
