# Prompt Templates

This directory intentionally contains evaluation-facing prompt format summaries,
not the original reference-construction prompts. Ground-truth-injection lines,
model names, examples with sample-specific answers, and API metadata are not
included in this anonymous data package.

For each subtask, use the fields in `../formal_templates/` to request the
required structured trace. The user prompt should contain only the input fields
from `../raw_benchmark_data/` and should not include the final answer or the
process reference states from `../process_evaluation_data/`.
