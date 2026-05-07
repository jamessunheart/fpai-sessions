.PHONY: map map-open audit audit-apply install-hooks help

PYTHON ?= python3

help:
	@echo "FPAI Cockpit — make targets"
	@echo ""
	@echo "  make map            Regenerate cockpit-map.html from NOW.md + catalog.json"
	@echo "  make map-open       Regenerate and open in default browser"
	@echo "  make audit          Audit catalog.json against SERVICES/ (untagged + stale)"
	@echo "  make audit-apply    Apply suggested tags into catalog.json"
	@echo "  make install-hooks  Install git post-commit hook (auto-refresh map)"
	@echo ""

map:
	@$(PYTHON) tools/gen_cockpit_map.py

map-open: map
	@open cockpit-map.html

audit:
	@$(PYTHON) tools/audit_catalog.py

audit-apply:
	@$(PYTHON) tools/audit_catalog.py --apply

install-hooks:
	@bash tools/git-hooks/install.sh
