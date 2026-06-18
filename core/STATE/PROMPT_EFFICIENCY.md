# Prompt Efficiency

Generated: 2026-06-18T20:03:50Z

| Prompt | Engine | Winner | Adopted | Pending | Quality | Avg tokens | Compression |
|---|---:|---:|---:|---:|---:|---:|---:|
| benchmark_improvement_spec | deterministic | compressed_guarded | true | false | 1.0 / baseline 1.0 | 91.5 / baseline 108.5 | 15.7% |
| council_pragmatist_lens | deterministic_fallback | compressed_guarded | false | true | 0.85 / baseline 0.85 | 17.0 / baseline 23.0 | 26.1% |

## Guard

A compressed variant is adopted only when quality is greater than or equal to baseline and token count is lower than baseline.
High-impact prompts are optimized into pending adoption and require human approval before active use.
Failed variants remain in the report as proof that the gate rejected under-specified compression.
