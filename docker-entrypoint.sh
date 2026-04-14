#!/bin/sh
set -e

if [ "$(id -u)" = "0" ]; then
    if [ -d /app/data ]; then
        chown -R app:app /app/data 2>/dev/null || true
    fi
    exec gosu app "$@"
fi

exec "$@"
