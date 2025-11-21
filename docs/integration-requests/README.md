# External Integration Request System

## Vision
You stay in the command center. Helpers bring capabilities to you.

## How It Works

### For the Commander (You):
1. Create a request file in this directory using the template
2. Helpers pick up requests and fulfill them
3. Completed integrations are delivered back via `COMPLETED/` directory
4. You integrate the API keys without ever leaving the command center

### For Helpers:
1. Check `OPEN_REQUESTS/` for pending integration tasks
2. Follow the instructions to obtain API keys/access
3. Deliver completed credentials to `COMPLETED/[request-name]/`
4. Update the status file

## Directory Structure

```
INTEGRATION_REQUESTS/
├── README.md (this file)
├── TEMPLATES/
│   └── api_request_template.md
├── OPEN_REQUESTS/
│   └── [active requests waiting for helpers]
├── IN_PROGRESS/
│   └── [requests being worked on]
└── COMPLETED/
    └── [delivered integrations ready to use]
```

## Current Need: Unsplash Photo API

See `OPEN_REQUESTS/unsplash_api.md` for details.

---

**This system enables autonomous capability acquisition - helpers extend the system without requiring commander intervention.**
