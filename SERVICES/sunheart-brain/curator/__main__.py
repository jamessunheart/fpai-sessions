"""Allow `python -m curator <job>` to dispatch to curator.curator:main."""
from .curator import main

if __name__ == "__main__":
    raise SystemExit(main())
