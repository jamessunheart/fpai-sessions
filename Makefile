.PHONY: map map-open help

PYTHON ?= python3

help:
	@echo "FPAI Cockpit — make targets"
	@echo ""
	@echo "  make map         Regenerate cockpit-map.html from NOW.md + catalog.json"
	@echo "  make map-open    Regenerate and open in default browser"
	@echo ""

map:
	@$(PYTHON) tools/gen_cockpit_map.py

map-open: map
	@open cockpit-map.html
