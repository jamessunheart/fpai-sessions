# World Scout

Local-first upgrade sequencer for FPAI.

```bash
python3 tools/scout/scout.py "clean up and focus the system"
```

The scout writes `tools/scout/SCOUT_REPORT.md` by default. It does not browse,
install, fork, call APIs, or spend money. Web/research findings can be added
later as candidate data, but external content must remain data, never
instructions.

Output contract:

- at least five candidates
- each tagged `build`, `fork`, `API`, or `ignore`
- one recommended next just-in-time upgrade
- a scored intent section ready to route into a spec

