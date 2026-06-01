# PRM/Formal-CoT Generation

`generate_prm.py` is the cleaned entry point for creating PRM-style process
evaluation data. It connects each active subtask to the corresponding
`formal_cot/<task>/<subtask>/prompt.py`, `parser.py`, and `verifier.py` modules.

The expected PRM record contains a model `raw_output` in the unified format:

```text
Step N [STEP_NAME]: natural language description
  FORMAL: A --> B
Answer: ...
```

When `raw_output` is present, no API call is made. When it is absent, the script
formats the released PRM-generation prompt and samples from an OpenAI-compatible
endpoint.

Example:

```bash
python -m prm_generation.generate_prm \
  --task rxn_pred \
  --subtask forward \
  --input-json input_records.json \
  --output-dir output/rxn_pred/forward \
  --model MODEL_NAME \
  --base-url OPENAI_COMPATIBLE_BASE_URL
```
