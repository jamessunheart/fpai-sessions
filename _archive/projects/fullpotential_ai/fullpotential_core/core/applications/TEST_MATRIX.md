# Application Test Matrix

| Application | Location | Test Command | Notes |
| --- | --- | --- | --- |
| Church Guidance Funnel | `core/applications/church-guidance-funnel` | `pytest` | Includes doc generation scripts; ensure virtualenv with `requirements.txt`. |
| Custom GPT Services | `core/applications/custom-gpt-services` | `pytest` (once tests added) | Currently lacks automated tests; manual endpoint smoke tests recommended. |
| FPAI Analytics | `core/applications/fpai-analytics` | _Not provided_ | Placeholder for future analytics suite; add tests before deployment. |
| I-Proactive | `core/applications/i-proactive` | _Not provided_ | Requires test harness once CLI/app sources restored. |
| Magnet Trading System | `core/applications/magnet-trading-system` | `python -m pytest tests/` | Survival fuse + leverage engine tests already in repo. |
| Mission Portal Frontend | `core/applications/systems/mission-portal/frontend` | `npm test` (pending package.json) | Only config present; add actual frontend project before tests run. |
| White Rock Landing | `core/applications/white-rock-landing` | `python treasury_tracker.py --dry-run` | Simple scripts; add pytest suite if logic expands. |

_Extend this table as more applications/droplets gain automated coverage. Use it as the source for future CI workflows._
