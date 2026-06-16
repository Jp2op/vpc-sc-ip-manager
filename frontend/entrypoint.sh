#!/bin/sh
BASE_PATH="${FRONTEND_BASE_PATH:-/llm-block/frontend/}"
BASE_PATH_NO_SLASH=$(echo "$BASE_PATH" | sed 's|/$||')

sed -i "s|FRONTEND_BASE_PATH_NO_SLASH|$BASE_PATH_NO_SLASH|g" /etc/nginx/conf.d/default.conf
sed -i "s|FRONTEND_BASE_PATH|$BASE_PATH|g" /etc/nginx/conf.d/default.conf

echo "Frontend serving at: $BASE_PATH"
exec "$@"
