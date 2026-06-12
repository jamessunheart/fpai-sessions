# First Challenge: Build a Telegram Command Module

## Overview

**Title:** Build Your First Module  
**Duration:** 7 days  
**Difficulty:** Beginner  
**Reward:** Apprentice Level 2 access

## Objective

Create a simple, useful Telegram command that demonstrates your ability to:
1. Understand the module structure
2. Write clean, working code
3. Follow the system patterns
4. Submit work for review

## The Challenge

Build a Telegram command module that does ONE of the following:

### Option A: Quote of the Day (`/quote`)
- Fetch or return an inspiring quote
- Format it nicely for Telegram
- Optionally include the author

### Option B: Simple Calculator (`/calc`)
- Parse a math expression (e.g., `/calc 5 + 3 * 2`)
- Return the result
- Handle errors gracefully

### Option C: Weather Check (`/weather`)
- Accept a city name
- Return current weather (use a free API)
- Format temperature and conditions

### Option D: Your Idea
- Propose your own command to Aria
- Get approval before building
- Must be simple and useful

## Requirements

1. **Location:** Your code must live in `/labs/{your_telegram_id}/modules/`
2. **Structure:** Follow the module schema (see `/core/standards/module.schema.json`)
3. **Documentation:** Include a README.md explaining:
   - What the command does
   - How to use it
   - Any dependencies
4. **Testing:** Command must work when tested

## Module Structure

```
/labs/{your_telegram_id}/modules/my-command/
├── README.md           # Documentation
├── module.json         # Module metadata (follows schema)
├── handler.py          # Main command handler
└── requirements.txt    # Dependencies (if any)
```

## Example module.json

```json
{
  "name": "quote-command",
  "version": "1.0.0",
  "description": "Returns an inspiring quote of the day",
  "author": "{your_name}",
  "command": "/quote",
  "type": "telegram_command",
  "entry": "handler.py",
  "dependencies": []
}
```

## Steps to Complete

1. **Tell Aria what you want to build**
   - "I want to build a /quote command"
   - Aria will help you set up the structure

2. **Write your code**
   - Ask Aria for help if stuck
   - She can read/write files in your workspace

3. **Test it**
   - Ask Aria to test the module
   - Fix any issues

4. **Submit for review**
   - Tell Aria: "I'm ready to submit my first challenge"
   - She'll move it to `/labs/submissions/`
   - James will review within 48 hours

## Success Criteria

- [ ] Code is in the correct location
- [ ] module.json follows the schema
- [ ] README.md is clear and helpful
- [ ] Command works when tested
- [ ] No security issues (no hardcoded secrets, etc.)

## Tips

- **Start simple** - A working simple command beats an incomplete complex one
- **Ask questions** - Aria is here to help, not to judge
- **Learn the patterns** - This teaches you how the system works
- **Have fun** - You're building real AI infrastructure!

## What Happens After

When you complete this challenge:
1. Your module may be added to the system
2. You unlock Level 2 access (more tools, more trust)
3. You get your next challenge: Build an AI Assistant

## Getting Help

Just message Aria:
- "I'm stuck on my first challenge"
- "How do I create a module?"
- "What's wrong with my code?"
- "Can you show me an example?"

She's programmed to guide, not do it for you. This helps you actually learn.

---

*Good luck, builder! Every expert was once a beginner.*


