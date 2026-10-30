# Microsoft Teams (messages)

Status: written from the Microsoft Graph docs and not yet tested. Note anything that doesn't match in `gaps`, and fix this file.

Always run this in a subagent, as with Slack. Use a Microsoft 365 connector that can search Teams messages through Graph search (`/search/query` with `entityTypes: ["chatMessage"]`). If no such tool can limit results to the user's own messages, **skip messages** and record a gap. Never fall back to listing chats or channel messages: that would load other people's messages.

**Identity.** Graph `/me` gives `id` and `displayName`. Store `id` as `messages.user_id`.

**Collect (in the subagent):**
1. Search chat messages with KQL `from:<user's email or UPN> sent>=<start - 1 day> sent<=<end + 1 day>`, following every page.
   - Graph returns a short `summary` per hit. Request only the fields needed: `chatId` or `channelIdentity`, `replyToId`, `createdDateTime`, `webUrl` and `body`.
   - Drop any hit whose `from.user.id` isn't the user's.
   - Drop hits from channels or teams whose name matches `messages.skip_channels`.
2. Group the messages:
   - A 1:1 or group chat (`chatId`) is one conversation, of kind `dm`. Name it after the other members, from the chat topic or members list if the connector gives them without loading messages. Otherwise use "Chat with N people".
   - Channel messages are grouped by `channelIdentity` plus the root message ID (`replyToId`, or the message's own ID if it's a root). Their kind is `thread`.
3. Apply the thresholds and classification in `SKILL.md`, step 3. The permalink is the `webUrl` of the user's first message in the conversation.
