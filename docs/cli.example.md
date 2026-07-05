# Open codex cli

OPENAI_API_KEY='sk-3addf894356ef827-xxxxxxxxxx' codex --dangerously-bypass-approvals-and-sandbox

systemd-run --user --scope --setenv=OPENAI_API_KEY='sk-3addf894356ef827-xxxxxxxxxx' -p MemoryHigh=2500M -p MemoryMax=3G codex --dangerously-bypass-approvals-and-sandbox

# claude

systemd-run --user --scope -p MemoryHigh=2500M -p MemoryMax=3G claude --dangerously-skip-permissions

# Test telegram

TELEGRAM_BOT_TOKEN="8733454851:AAGwaEX_xdff7Hy55g_xxxxxxxxxx" TELEGRAM_CHAT_ID="888xxxxxxxxxx" curl -sS --fail-with-body --connect-timeout 10 --max-time 20 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" --data-urlencode "text=✅ Telegram test from $(hostname) at $(date --iso-8601=seconds)"

# Run task range PROMPT

run prompt docs\prompts\04_run_task_to_task.md task 07 - 08 TELEGRAM_BOT_TOKEN="8733454851:AAGwaEX_xdff7Hy55g_xxxxxxxxxx" TELEGRAM_CHAT_ID="888xxxxxxxxxx"

# Run all tasks PROMPT

run prompt docs\prompts\03_run_all_tasks_subagent.md TELEGRAM_BOT_TOKEN="8733454851:AAGwaEX_xdff7Hy55g_xxxxxxxxxx" TELEGRAM_CHAT_ID="888xxxxxxxxxx"
