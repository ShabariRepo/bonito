#!/bin/bash
# Notion Update Helper
# Usage: ./scripts/notion-update.sh "changelog entry" "category"
# Categories: infrastructure, feature, fix, decision, milestone

TOKEN="$(grep NOTION_API_KEY ../.env.secrets 2>/dev/null | cut -d= -f2 || echo $NOTION_API_KEY)"
CHANGELOG_ID="3000bd81-9128-811c-ba5a-ca4ad783e62f"

if [ -z "$1" ]; then
  echo "Usage: $0 'entry text' [category]"
  exit 1
fi

ENTRY="$1"
CATEGORY="${2:-feature}"
DATE=$(date +%Y-%m-%d)

# Append to changelog
curl -s "https://api.notion.com/v1/blocks/${CHANGELOG_ID}/children" -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d "{
    \"children\": [{
      \"object\": \"block\",
      \"type\": \"bulleted_list_item\",
      \"bulleted_list_item\": {
        \"rich_text\": [{\"type\": \"text\", \"text\": {\"content\": \"[$DATE] [$CATEGORY] $ENTRY\"}}]
      }
    }]
  }" > /dev/null 2>&1

echo "✅ Notion changelog updated: $ENTRY"
