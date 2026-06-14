#!/bin/bash
# Fix nginx config - Close whaletrack/api block before ads section

CONFIG_FILE="/etc/nginx/sites-available/fullpotential.ai"

# Find where ads section starts
ADS_LINE=$(grep -n "# Ad Portal" "$CONFIG_FILE" | head -1 | cut -d: -f1)

if [ -z "$ADS_LINE" ]; then
    echo "❌ Could not find ads section"
    exit 1
fi

# Check if whaletrack/api block is open before ads section
WHALETRACK_LINE=$(grep -n "location ^~ /dashboards/whaletrack/api/" "$CONFIG_FILE" | head -1 | cut -d: -f1)

if [ -n "$WHALETRACK_LINE" ] && [ "$WHALETRACK_LINE" -lt "$ADS_LINE" ]; then
    echo "Found whaletrack block at line $WHALETRACK_LINE, ads at line $ADS_LINE"
    
    # Count braces between them
    BRACE_COUNT=1
    for ((i=$WHALETRACK_LINE+1; i<$ADS_LINE; i++)); do
        LINE=$(sed -n "${i}p" "$CONFIG_FILE")
        OPEN=$(echo "$LINE" | grep -o "{" | wc -l)
        CLOSE=$(echo "$LINE" | grep -o "}" | wc -l)
        BRACE_COUNT=$((BRACE_COUNT + OPEN - CLOSE))
    done
    
    if [ "$BRACE_COUNT" -gt 0 ]; then
        echo "❌ Whaletrack block not closed (brace count: $BRACE_COUNT)"
        echo "Closing it..."
        
        # Insert closing brace before ads section
        sed -i "${ADS_LINE}i\\
    }\\
\\
" "$CONFIG_FILE"
        
        echo "✅ Added closing brace"
    else
        echo "✅ Whaletrack block is closed"
    fi
fi

# Test and reload
nginx -t && systemctl reload nginx && echo "✅ Nginx reloaded successfully!"

