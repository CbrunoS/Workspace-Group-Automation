#!/bin/zsh

cd "/Users/admin/dev/workspace-group-automation" || exit 1

"/Users/admin/dev/workspace-group-automation/venv/bin/python3" -m app.main >> "/Users/admin/dev/workspace-group-automation/logs/cron.log" 2>&1