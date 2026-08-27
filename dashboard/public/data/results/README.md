# runner/result/

Auto-populated run outputs, one subfolder per agent (`s3soa/`, `soa/`, `eoa/`,
`poa/`). Each run of `runner/run.py` writes a JSON file here named:

```
{scenario_id}__{agent}__{YYYYMMDD_HHMMSS}.json
```

`dashboard/public/data/results` is a symlink to this directory — the dashboard reads run
outputs from here only. See the root [README](../../README.md#how-results-are-saved) for the
file schema.
