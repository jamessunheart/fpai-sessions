#!/bin/bash

while true; do
    if ! docker ps | grep -q airtable-server; then
        echo "Container stopped, restarting..."
        cd /root/droplet-2
        ./deploy.sh
    fi
    sleep 30
done
