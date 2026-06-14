# Gratitude Module

Build a daily gratitude practice with Aria.

## Usage

**Log gratitude:**
```
/gratitude I'm grateful for the beautiful sunrise today
```

**View history:**
```
/gratitude
```

## Features

- Personal gratitude journal per user
- Timestamps for each entry
- Encouragement at milestones (1, 7, 30, 100 entries)
- Shows last 7 entries when viewing

## Why Gratitude?

Research shows that regular gratitude practice:
- Increases happiness and life satisfaction
- Reduces stress and anxiety
- Improves sleep quality
- Strengthens relationships
- Builds resilience

## Data Storage

Entries are stored in JSON format at:
`/opt/fpai/data/gratitude/user_{id}.json`

Each user's data is private and separate.


