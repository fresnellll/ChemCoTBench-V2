# Molecule Editing Construction

Main paper-aligned flow:

1. `extract_reaction_edits.py`: extract add/delete/substitute source-target
   edits from atom-mapped Schneider 50K reactions.
2. `generate_edit_instructions.py`: generate concise site-specific edit
   instructions with an OpenAI-compatible model.
3. `assemble_moledit.py`: apply instruction-quality filters, deduplicate by
   source-target pair, and sample 300 examples for each edit type.

Historical difficulty labels and probe scripts are intentionally not included
in the released construction path.

