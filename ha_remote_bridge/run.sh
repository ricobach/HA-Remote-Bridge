#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "Starting HA Remote Bridge"
exec python3 /app/compat_runner_v33.py
