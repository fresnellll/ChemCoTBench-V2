# Reaction Prediction Construction

Main paper-aligned flow:

1. `assemble_reaction_tasks.py`: assemble forward prediction, byproduct,
   retrosynthesis, NEPP, and reaction-component recommendation tasks from
   derived reaction pools.
2. `build_condition_tasks.py`: build condition-ranking and yield-prediction
   tasks from public HTE tables, including random label shuffling for condition
   ranking.
3. `build_template_and_mechanism_tasks.py`: assemble reaction-template and
   mechanism-selection tasks from derived template/mechanism pools.

The release excludes historical probe scripts and difficulty-tag generation.

