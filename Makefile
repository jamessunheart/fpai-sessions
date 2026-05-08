.PHONY: map map-open audit audit-apply agreements install-hooks help

PYTHON ?= python3

help:
	@echo "FPAI Cockpit — make targets"
	@echo ""
	@echo "  make map            Regenerate cockpit-map.html (also rebuilds agreements registry)"
	@echo "  make map-open       Regenerate and open in default browser"
	@echo "  make agreements     Rebuild AGREEMENTS/INDEX.md + registry.json from front-matter"
	@echo "  make audit          Audit catalog.json against SERVICES/ (untagged + stale)"
	@echo "  make audit-apply    Apply suggested tags into catalog.json"
	@echo "  make install-hooks  Install git post-commit hook (auto-refresh map)"
	@echo ""

agreements:
	@$(PYTHON) tools/registry/build_index.py

map: agreements
	@$(PYTHON) tools/gen_cockpit_map.py

map-open: map
	@open cockpit-map.html

audit:
	@$(PYTHON) tools/audit_catalog.py

audit-apply:
	@$(PYTHON) tools/audit_catalog.py --apply

install-hooks:
	@bash tools/git-hooks/install.sh
