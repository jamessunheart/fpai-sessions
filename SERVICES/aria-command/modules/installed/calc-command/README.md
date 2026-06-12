# Calculator Module

A safe calculator for quick math in Telegram.

## Usage

```
/calc <expression>
```

## Examples

- `/calc 5 + 3 * 2` → 11
- `/calc 100 * 0.15` → 15.0 (tip calculator!)
- `/calc sqrt(16)` → 4.0
- `/calc (50 + 30) / 2` → 40.0
- `/calc sin(pi/2)` → 1.0

## Available Functions

- `sqrt(x)` - Square root
- `sin(x)`, `cos(x)`, `tan(x)` - Trigonometry
- `log(x)`, `log10(x)` - Logarithms
- `abs(x)` - Absolute value
- `round(x)` - Round to nearest integer
- `min(a,b)`, `max(a,b)` - Minimum/maximum
- `pi`, `e` - Constants

## Security

This module uses a restricted eval with only safe math operations.
No system access, file access, or imports are possible.


