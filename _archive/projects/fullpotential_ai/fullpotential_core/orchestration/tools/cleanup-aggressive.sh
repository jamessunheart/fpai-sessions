#!/bin/bash
# Aggressive cleanup - Move ALL non-essential files

echo "🧹 AGGRESSIVE CLEANUP - Moving all non-essential files..."

# Move ALL remaining .md files except START_HERE, README, BOOT
find . -maxdepth 1 -name "*.md" ! -name "START_HERE.md" ! -name "README.md" ! -name "BOOT.md" -exec mv {} .archive/deprecated/ \; 2>/dev/null

# Move all .txt files
find . -maxdepth 1 -name "*.txt" -exec mv {} .archive/deprecated/ \; 2>/dev/null

# Move remaining .sh scripts
find . -maxdepth 1 -name "*.sh" ! -name "reorganize.sh" ! -name "cleanup-aggressive.sh" -exec mv {} _scripts/ \; 2>/dev/null

# Move .json files
find . -maxdepth 1 -name "*.json" -exec mv {} .archive/deprecated/ \; 2>/dev/null

# Move .py files
find . -maxdepth 1 -name "*.py" -exec mv {} _scripts/ \; 2>/dev/null

# Move .log files
find . -maxdepth 1 -name "*.log" -exec mv {} .archive/deprecated/ \; 2>/dev/null

echo "✅ Cleanup complete - Root is now minimal"
ls -1 | head -30
