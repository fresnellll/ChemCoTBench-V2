# Molecular Optimization Construction

Main paper-aligned flow:

1. `assemble_single_objective.py`: sample single-objective MMP records for
   LogP, QED, solubility, DRD2, JNK3, and GSK3beta.
2. `assemble_dual_objective.py`: sample dual-objective records from multistep
   MMP paths and emit both per-pair and combined files.

The release scripts keep objective thresholds, structural metadata, and
task-balanced sampling. Historical difficulty labels and probing logic are not
part of the released construction path.

