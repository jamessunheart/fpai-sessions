# Prompt Efficiency

Generated: 2026-06-18T19:53:47Z

| Prompt | Winner | Adopted | Quality | Avg tokens | Compression |
|---|---:|---:|---:|---:|---:|
| benchmark_improvement_spec | compressed_guarded | true | 1.0 / baseline 1.0 | 91.5 / baseline 108.5 | 15.7% |

## Guard

A compressed variant is adopted only when quality is greater than or equal to baseline and token count is lower than baseline.
Failed variants remain in the report as proof that the gate rejected under-specified compression.
