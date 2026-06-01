# Evaluation Prompt Format Summary

Evaluation prompts should expose the required structured fields without final-answer labels.
The following subtask sections list the step fields expected by the process-level schema.

## mol_edit/add_v2
- `step1_anchor_element`
- `step1_anchor_idx`
- `step1_leaving_smiles`
- `step2_frag_smiles`
- `step2_heavy_atoms`
- `step3_product_smiles`
- `step4_heavy_delta`
- `step4_n_heavy_prod`
- `step4_n_heavy_src`
- `step5_n_rings_prod`
- `step5_n_rings_src`
- `step5_ring_delta`

## mol_edit/delete_v2
- `step1_anchor_element`
- `step1_anchor_idx`
- `step1_remove_group`
- `step2_heavy_atoms`
- `step2_remove_smiles`
- `step3_product_smiles`
- `step4_heavy_delta`
- `step4_n_heavy_prod`
- `step4_n_heavy_src`
- `step5_n_rings_prod`
- `step5_n_rings_src`
- `step5_ring_delta`

## mol_edit/substitute_v2
- `step1_add_fragment_smiles`
- `step1_anchor_element`
- `step1_anchor_idx`
- `step1_remove_group_smiles`
- `step2_remove_heavy`
- `step3_add_heavy`
- `step4_product_smiles`
- `step5_heavy_delta`
- `step5_n_heavy_prod`
- `step5_n_heavy_src`
- `step6_n_rings_prod`
- `step6_n_rings_src`
- `step6_ring_delta`

## mol_opt/drd
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/drd_logp
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/drd_solubility
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/gsk
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/gsk_logp
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/jnk
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/logp
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/logp_qed
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/logp_solubility
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/qed
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/qed_solubility
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_opt/solubility
- `step1_scaffold_smiles`
- `step2_fg_added`
- `step2_fg_removed`
- `step3_predicted_smiles`
- `step4_scaffold_claimed`
- `step5_fg_consistent_claimed`

## mol_und/fg_detect
- `step1_alts`
- `step1_smarts`
- `step2_n`
- `step3_count`

## mol_und/murcko_scaffold
- `step1_n_mol_rings`
- `step2_scaffold`
- `step3_n_scaf_rings`
- `step4_ring_match`
- `step5_substructure`

## mol_und/ring_count
- `step1_alts`
- `step1_smarts`
- `step2_total`
- `step3_n`
- `step4_count`
- `step5_rejected`

## mol_und/ring_sys_scaffold
- `step1_n_mol`
- `step2_n_scaf`
- `step3_non_ring`
- `step4_predict`

## mol_und/smiles_equivalent
- `step1_canonical_a`
- `step1_formula_a`
- `step2_canonical_b`
- `step2_formula_b`
- `step3_formula_match`
- `step3_identical`
- `step4_canonical_equal`
- `step4_predict`
- `step5_predict`

## rxn_pred/byproduct
- `step1_fg_list`
- `step1_fg_list_str`
- `step2_rxn_type`
- `step3_atomic_delta`
- `step3_atomic_delta_str`
- `step4_lf_smiles`
- `step5_fragment_in_reactant`
- `step6_byproduct_smiles`

## rxn_pred/condition_ranking
- `step1_rxn_class`
- `step2_decision_factor`
- `step3_pair_diffs`
- `step4_pairwise_prefs`
- `step5_ranking`
- `step6_top2_support`

## rxn_pred/forward
- `step1_fg_list`
- `step1_fg_list_str`
- `step1_line`
- `step2_line`
- `step2_rxn_type`
- `step3_line`
- `step3_mechanism`
- `step4_line`
- `step4_predicted_smi`
- `step5_line`
- `step5_mol_valid`
- `step6_bond_formed`
- `step6_line`

## rxn_pred/mech_sel
- `step1_reagent_types`
- `step1_smarts_list`
- `step2_rxn_type`
- `step3_eliminated`
- `step4_remaining`
- `step5_selected`

## rxn_pred/nepp
- `step1_net_charge`
- `step1_reactants_smi`
- `step2_elem_mech`
- `step3_bond_change`
- `step4_predicted_smi`
- `step5_product_charge`
- `step6_charge_balanced`
- `step7_atom_conserved`
- `step_annotation`

## rxn_pred/rcr_catalyst
- `step1_rxn_cls`
- `step2_core_transform`
- `step3_catalyst_role`
- `step4_catalyst_class`
- `step5_predicted_catalyst_smiles`
- `step5_predicted_smi`
- `step6_self_consistent`

## rxn_pred/rcr_reagent
- `step1_rxn_class`
- `step2_core_transformation`
- `step2_rxn_smiles`
- `step3_reagent_slot`
- `step4_reagent_strategy`
- `step5_component_mode`
- `step6_reagent_class`
- `step7_predicted_reagent_smiles`
- `step8_self_consistent`

## rxn_pred/rcr_solvent
- `step1_rxn_class`
- `step2_core_transformation`
- `step2_rxn_smiles`
- `step3_proticity`
- `step4_polarity`
- `step5_predicted_solvent_smiles`
- `step6_self_consistent`

## rxn_pred/retro
- `step1_fg_list`
- `step2_rxn_type`
- `step3_mechanism`
- `step4_reactant_smi`
- `step5_all_valid`
- `step6_bond_broken`
- `step7_fwd_match`
- `step7_fwd_note`

## rxn_pred/rxn_template
- `step1_bond_changes`
- `step2_rxn_type`
- `step3_mechanism`
- `step4_proposed_smarts`
- `step5_smarts_parseable`
- `step6_selected_option`

## rxn_pred/yield_pred
- `step1_rxn_class`
- `step2_halide_type`
- `step3_nucleophile_form`
- `step3_nucleophile_type`
- `step4_ligand_class`
- `step5_predicted_yield`
- `step6_self_consistent`
