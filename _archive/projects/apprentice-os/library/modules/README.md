# Modules Library

> Reusable capabilities that can be installed on assistants.

## Structure

```
/modules
├── /official        # Maintained by Full Potential
│   └── (coming soon)
├── /community       # Created by apprentices
│   └── (coming soon)
└── README.md
```

## Creating a Module

Modules follow the schema defined in `/core/standards/module.schema.json`.

### Required Fields

```json
{
  "id": "my-module",
  "name": "My Module",
  "version": "1.0.0",
  "capabilities": [...],
  "permissions": [...]
}
```

### Capabilities

Each capability defines what the module can do:

- `action` - Performs an operation
- `query` - Retrieves data
- `trigger` - Fires on conditions
- `transform` - Modifies data

### Permissions

Modules must declare what permissions they need:

- `read_files` / `write_files`
- `execute_commands`
- `network_access`
- `memory_read` / `memory_write`
- `send_messages`
- `api_calls`
- `database_read` / `database_write`

## Planned Official Modules

1. **calendar-sync** - Connect to Google Calendar
2. **trading-signals** - WhaleTrack integration
3. **code-review** - Automated PR reviews
4. **health-check** - System monitoring
5. **voice-interface** - ElevenLabs voice

## Contributing

Apprentices can create modules that get reviewed and added to the library.
Community modules go through governance review before becoming official.

---

*This library grows as apprentices build and share capabilities.*


