#!/usr/bin/env python3
"""Aggregate ChemCoTBench-V2 evaluation summaries into 18 reporting tasks.

The implementation benchmark still has 31 active subtasks.  This script reads
the per-subtask ``summary.json`` files and produces paper-facing tables under
``results/evaluation/reporting_tasks``.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = PROJECT_ROOT / "results" / "evaluation"
DEFAULT_OUT_DIR = EVAL_ROOT / "reporting_tasks"


MODELS = [
    ("qwen_qwen3.5-plus", "Qwen3.5+"),
    ("dpsk-V4-Pro", "DeepSeek-V4"),
    ("deepseek-v3.2", "DeepSeek-V3.2"),
    ("doubao-seed-2-0-pro-260215", "Doubao-2Pro"),
    ("zai-org_glm-5.1", "GLM-5.1"),
    ("gpt-5.2", "GPT-5.2"),
    ("gemini-3.1-pro-preview", "Gemini-3.1"),
    ("claude-sonnet-4-6", "Claude-Sonnet"),
]


@dataclass(frozen=True)
class ReportingTask:
    family: str
    name: str
    subtasks: tuple[tuple[str, str], ...]
    n: int
    layer1_label: str
    layer1_kind: str


REPORTING_TASKS = [
    ReportingTask("MolEdit", "Add", (("mol_edit", "add_v2"),), 300, "Exact Acc ↑", "exact_acc"),
    ReportingTask("MolEdit", "Delete", (("mol_edit", "delete_v2"),), 300, "Exact Acc ↑", "exact_acc"),
    ReportingTask("MolEdit", "Substitute", (("mol_edit", "substitute_v2"),), 300, "Exact Acc ↑", "exact_acc"),
    ReportingTask("MolUnd", "Functional Group", (("mol_und", "fg_detect"),), 300, "MAE ↓", "mae"),
    ReportingTask("MolUnd", "Ring Count", (("mol_und", "ring_count"),), 300, "MAE ↓", "mae"),
    ReportingTask("MolUnd", "Murcko Scaffold", (("mol_und", "murcko_scaffold"),), 300, "Tanimoto ↑", "tanimoto"),
    ReportingTask("MolUnd", "Ring-System Scaffold", (("mol_und", "ring_sys_scaffold"),), 300, "Exact Acc ↑", "exact_acc"),
    ReportingTask("MolUnd", "SMILES Equivalence", (("mol_und", "smiles_equivalent"),), 300, "Exact Acc ↑", "exact_acc"),
    ReportingTask(
        "RxnPred",
        "Product-Level Prediction",
        (("rxn_pred", "forward"), ("rxn_pred", "byproduct"), ("rxn_pred", "nepp")),
        600,
        "Top-1 Acc ↑",
        "top1",
    ),
    ReportingTask("RxnPred", "Retrosynthesis", (("rxn_pred", "retro"),), 200, "Top-1 Acc ↑", "top1"),
    ReportingTask(
        "RxnPred",
        "Template/Mechanism Reasoning",
        (("rxn_pred", "rxn_template"), ("rxn_pred", "mech_sel")),
        400,
        "Top-1 Acc ↑",
        "top1",
    ),
    ReportingTask(
        "RxnPred",
        "Component Recommendation",
        (("rxn_pred", "rcr_catalyst"), ("rxn_pred", "rcr_reagent"), ("rxn_pred", "rcr_solvent")),
        600,
        "Top-1 Acc ↑",
        "top1",
    ),
    ReportingTask(
        "RxnPred",
        "Condition Ranking",
        (("rxn_pred", "condition_ranking"),),
        200,
        "Top-1 Acc ↑",
        "top1",
    ),
    ReportingTask(
        "RxnPred",
        "Yield Prediction",
        (("rxn_pred", "yield_pred"),),
        200,
        "MAE ↓",
        "yield_mae",
    ),
    ReportingTask(
        "MolOpt",
        "PhysChem-Single",
        (("mol_opt", "logp"), ("mol_opt", "qed"), ("mol_opt", "solubility")),
        360,
        "SR ↑",
        "sr",
    ),
    ReportingTask(
        "MolOpt",
        "BioTarget-Single",
        (("mol_opt", "drd"), ("mol_opt", "jnk"), ("mol_opt", "gsk")),
        360,
        "SR ↑",
        "sr",
    ),
    ReportingTask(
        "MolOpt",
        "PhysChem-Dual",
        (("mol_opt", "logp_qed"), ("mol_opt", "logp_solubility"), ("mol_opt", "qed_solubility")),
        150,
        "Dual-SR ↑",
        "dual_sr",
    ),
    ReportingTask(
        "MolOpt",
        "BioTarget-Dual",
        (("mol_opt", "drd_logp"), ("mol_opt", "drd_solubility"), ("mol_opt", "gsk_logp")),
        150,
        "Dual-SR ↑",
        "dual_sr",
    ),
]


ABLATION_TASKS = {
    "mol_und": [
        ("fg_detect", "mean_mae"),
        ("ring_count", "mean_mae"),
        ("murcko_scaffold", "avg_tanimoto"),
        ("ring_sys_scaffold", "exact_match_acc"),
        ("smiles_equivalent", "exact_match_acc"),
    ],
    "mol_opt": [
        ("logp", "sr_pct"),
        ("qed", "sr_pct"),
        ("solubility", "sr_pct"),
        ("drd", "sr_pct"),
        ("gsk", "sr_pct"),
        ("jnk", "sr_pct"),
        ("logp_qed", "dual_sr_pct"),
        ("logp_solubility", "dual_sr_pct"),
        ("qed_solubility", "dual_sr_pct"),
        ("drd_logp", "dual_sr_pct"),
        ("drd_solubility", "dual_sr_pct"),
        ("gsk_logp", "dual_sr_pct"),
    ],
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2, ensure_ascii=False)


def n_from_summary(summary: dict[str, Any]) -> int:
    for value in (
        summary.get("n_total"),
        summary.get("config", {}).get("n_samples") if isinstance(summary.get("config"), dict) else None,
        summary.get("layer1", {}).get("n") if isinstance(summary.get("layer1"), dict) else None,
        summary.get("layer2", {}).get("n") if isinstance(summary.get("layer2"), dict) else None,
        summary.get("layer3", {}).get("n") if isinstance(summary.get("layer3"), dict) else None,
    ):
        if isinstance(value, int) and value > 0:
            return value
    raise ValueError("Cannot infer sample count from summary")


def weighted_mean(values: list[tuple[float, int]]) -> float | None:
    values = [(float(v), int(n)) for v, n in values if v is not None and n > 0]
    if not values:
        return None
    return sum(v * n for v, n in values) / sum(n for _, n in values)


def summary_path(task: str, subtask: str, model: str) -> Path:
    return EVAL_ROOT / task / subtask / model / "summary.json"


def load_model_summaries(model: str) -> dict[tuple[str, str], dict[str, Any]]:
    summaries = {}
    missing = []
    for reporting in REPORTING_TASKS:
        for task, subtask in reporting.subtasks:
            path = summary_path(task, subtask, model)
            if not path.exists():
                missing.append(f"{task}/{subtask}")
                continue
            summaries[(task, subtask)] = load_json(path)
    if missing:
        raise FileNotFoundError(f"{model} is missing summaries: {', '.join(missing)}")
    return summaries


def layer1_value(kind: str, items: list[tuple[str, str, dict[str, Any]]]) -> dict[str, Any]:
    key_by_kind = {
        "exact_acc": "exact_match_acc",
        "mae": "mean_mae",
        "yield_mae": "mae",
        "tanimoto": "avg_tanimoto",
        "top1": "top1_acc",
        "sr": "sr_pct",
        "dual_sr": "dual_sr_pct",
    }
    key = key_by_kind[kind]
    values = []
    for _, _, summary in items:
        values.append((summary["layer1"][key], n_from_summary(summary)))
    value = weighted_mean(values)
    return {"kind": kind, "value": value, "display": format_layer1(kind, value)}


def layer2_value(items: list[tuple[str, str, dict[str, Any]]]) -> float | None:
    values = []
    for _, _, summary in items:
        layer2 = summary.get("layer2", {})
        score = layer2.get("state_score", layer2.get("avg_state_score"))
        values.append((score, n_from_summary(summary)))
    return weighted_mean(values)


def layer3_value(items: list[tuple[str, str, dict[str, Any]]]) -> dict[str, Any]:
    if all(task == "mol_opt" for task, _, _ in items):
        value = weighted_mean([
            (summary.get("layer3", {}).get("avg_step_score"), n_from_summary(summary))
            for _, _, summary in items
        ])
        return {"kind": "molopt_step", "avg_step_score": value, "display": format_float(value, 3)}

    type1 = weighted_mean([
        (summary.get("layer3", {}).get("type1", {}).get("all_pass_rate"), n_from_summary(summary))
        for _, _, summary in items
    ])
    type2 = weighted_mean([
        (summary.get("layer3", {}).get("type2", {}).get("all_fields_match_rate"), n_from_summary(summary))
        for _, _, summary in items
    ])
    return {
        "kind": "type1_type2",
        "type1_all_pass": type1,
        "type2_all_match": type2,
        "display": f"{format_float(type1, 3)} / {format_float(type2, 3)}",
    }


def format_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def format_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{100 * value:.1f}"


def format_layer1(kind: str, value: float | None) -> str:
    if value is None:
        return "-"
    if kind in {"exact_acc", "top1"}:
        return format_percent(value)
    if kind in {"sr", "dual_sr"}:
        return f"{value:.1f}"
    if kind in {"mae", "yield_mae", "tanimoto"}:
        return f"{value:.3f}"
    return format_float(value, 3)


def compute_reporting_results(models: list[tuple[str, str]]) -> dict[str, Any]:
    model_summaries = {model: load_model_summaries(model) for model, _ in models}
    rows = []
    for reporting in REPORTING_TASKS:
        row = {
            "family": reporting.family,
            "reporting_task": reporting.name,
            "subtasks": [f"{task}/{subtask}" for task, subtask in reporting.subtasks],
            "n": reporting.n,
            "layer1_label": reporting.layer1_label,
            "models": {},
        }
        for model, label in models:
            items = [
                (task, subtask, model_summaries[model][(task, subtask)])
                for task, subtask in reporting.subtasks
            ]
            row["models"][label] = {
                "model_dir": model,
                "layer1": layer1_value(reporting.layer1_kind, items),
                "layer2_state_score": layer2_value(items),
                "layer3": layer3_value(items),
            }
        rows.append(row)
    return {
        "config": {
            "models": [{"dir": model, "label": label} for model, label in models],
            "n_reporting_tasks": len(REPORTING_TASKS),
            "n_active_samples": 5620,
            "aggregation": "Weighted by active sample count over 31 implementation subtasks.",
        },
        "reporting_tasks": [
            {
                "family": rt.family,
                "reporting_task": rt.name,
                "subtasks": [f"{task}/{subtask}" for task, subtask in rt.subtasks],
                "n": rt.n,
                "layer1_label": rt.layer1_label,
            }
            for rt in REPORTING_TASKS
        ],
        "rows": rows,
    }


def write_csvs(result: dict[str, Any], out_dir: Path) -> None:
    labels = [m["label"] for m in result["config"]["models"]]
    for table_name, getter in (
        ("layer1.csv", lambda cell: cell["layer1"]["display"]),
        ("layer2.csv", lambda cell: format_float(cell["layer2_state_score"], 4)),
        ("layer3.csv", lambda cell: cell["layer3"]["display"]),
    ):
        with (out_dir / table_name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            first_metric = "Layer 1 metric" if table_name == "layer1.csv" else "Metric"
            writer.writerow(["Family", "Reporting task", "n", first_metric, *labels])
            for row in result["rows"]:
                metric = row["layer1_label"] if table_name == "layer1.csv" else (
                    "State Score" if table_name == "layer2.csv" else (
                        "Avg Step" if row["family"] == "MolOpt" else "Type I / Type II"
                    )
                )
                writer.writerow([
                    row["family"],
                    row["reporting_task"],
                    row["n"],
                    metric,
                    *[getter(row["models"][label]) for label in labels],
                ])


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def rows_by_family(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in result["rows"]:
        grouped.setdefault(row["family"], []).append(row)
    return grouped


def layer1_best_rows(result: dict[str, Any]) -> list[list[str]]:
    labels = [m["label"] for m in result["config"]["models"]]
    rows: list[list[str]] = []
    for row in result["rows"]:
        values = []
        kind = None
        for label in labels:
            layer1 = row["models"][label]["layer1"]
            kind = layer1["kind"]
            values.append((label, layer1["value"], layer1["display"]))
        lower_better = kind in {"mae", "yield_mae"}
        best = min(values, key=lambda item: item[1]) if lower_better else max(values, key=lambda item: item[1])
        rows.append([
            row["family"],
            row["reporting_task"],
            row["layer1_label"],
            f"{best[0]} ({best[2]})",
        ])
    return rows


def overview_rows(result: dict[str, Any]) -> tuple[list[list[str]], list[list[str]]]:
    labels = [m["label"] for m in result["config"]["models"]]
    layer2_rows = []
    for label in labels:
        avg = sum(row["models"][label]["layer2_state_score"] for row in result["rows"]) / len(result["rows"])
        layer2_rows.append([label, f"{avg:.3f}"])

    layer3_rows = []
    for family, family_rows in rows_by_family(result).items():
        for label in labels:
            if family == "MolOpt":
                avg = sum(row["models"][label]["layer3"]["avg_step_score"] for row in family_rows) / len(family_rows)
                layer3_rows.append([family, label, "Avg Step", f"{avg:.3f}"])
            else:
                avg_type1 = sum(row["models"][label]["layer3"]["type1_all_pass"] for row in family_rows) / len(family_rows)
                avg_type2 = sum(row["models"][label]["layer3"]["type2_all_match"] for row in family_rows) / len(family_rows)
                layer3_rows.append([family, label, "Type I / Type II", f"{avg_type1:.3f} / {avg_type2:.3f}"])
    return layer2_rows, layer3_rows


def build_main_markdown(result: dict[str, Any], ablation: dict[str, Any]) -> str:
    labels = [m["label"] for m in result["config"]["models"]]
    model_rows = [[m["label"], m["dir"]] for m in result["config"]["models"]]
    layer2_overview, layer3_overview = overview_rows(result)
    lines = [
        "# 模型评测结果汇总（18 个 Reporting Task 标签版）",
        "",
        "本文档记录当前 ChemCoTBench-V2 压缩数据集与统一评测框架下，8 个模型在 18 个论文展示粒度 reporting tasks 上的真实复算结果。底层代码框架仍然是 31 个 active implementation subtasks；18 个 reporting tasks 只用于论文呈现和结果整理，不改变 benchmark 样本或评测代码。",
        "",
        "数据来源为 `results/evaluation/{task}/{subtask}/{model}/summary.json`。本次结果已在 `chemcot` 环境下对 8 个模型执行 eval-only 复算，并由 `scripts/aggregate_reporting_tasks.py` 聚合生成。当前 active benchmark 共 **5620** 条样本：MolEdit 900、MolUnd 1500、RxnPred 2200、MolOpt 1020。",
        "",
        "## 1. 模型与数据来源",
        "",
        markdown_table(["展示名", "结果目录 / 模型标识"], model_rows),
        "",
        "生成文件：",
        "",
        "- `docs/模型评测结果汇总.md`：本文档。",
        "- `results/evaluation/reporting_tasks/reporting_tasks_18.json`：结构化汇总结果。",
        "- `results/evaluation/reporting_tasks/layer1.csv`、`layer2.csv`、`layer3.csv`：三层结果表。",
        "- `results/evaluation/reporting_tasks/ablation_layer1.json`：对比实验 Layer 1 汇总。",
        "",
        "完整性检查：18 个 reporting tasks、8 个模型、Layer 1/2/3 三层结果均齐全；总计 `18 × 8 × 3 = 432` 个主结果字段，无缺失。",
        "",
        "## 2. Reporting Task 标签",
        "",
    ]
    task_rows = []
    for task in result["reporting_tasks"]:
        task_rows.append([
            task["family"],
            task["reporting_task"],
            ", ".join(x.split("/", 1)[1] for x in task["subtasks"]),
            task["n"],
            task["layer1_label"],
        ])
    lines.append(markdown_table(["任务族", "Reporting task", "包含的底层子任务", "n", "Layer 1 主指标"], task_rows))

    lines.extend([
        "",
        "## 3. 评测口径",
        "",
        "- Layer 1 评测最终答案正确性。Acc、Top-1、SR、Dual-SR 使用百分数；Tanimoto 使用 0-1 分数；MAE 越低越好。",
        "- Layer 2 评测 structured output 是否符合 scientist reasoning template，以及 V 点/状态字段是否完整和自洽。高 Layer 2 不代表最终答案正确，只代表结构化模板依从性高。",
        "- Layer 3 评测 formal CoT / PRM GT 下的 step-wise reasoning correctness。MolEdit、MolUnd、RxnPred 使用 `Type I all-pass / Type II all-match`；MolOpt 使用 `Avg Step Score`。",
        "- 聚合项按 active 样本数加权平均。单底层子任务对应的 reporting task 直接沿用该子任务结果。",
        "- `Condition Ranking` 与 `Yield Prediction` 分别作为独立 reporting tasks：前者 Layer 1 使用 Top-1 Acc，后者 Layer 1 使用 MAE，避免同一任务下混合方向和语义不同的主指标。",
        "",
        "## 4. Layer 1：最终答案主指标",
        "",
        "Acc/SR 用百分数；Tanimoto 为 0-1；MAE 越低越好。`Condition Ranking` 使用 Top-1 Acc，`Yield Prediction` 使用 MAE。",
    ])
    for family, rows in rows_by_family(result).items():
        lines.extend(["", f"### {family}", ""])
        table_rows = []
        for row in rows:
            table_rows.append([
                row["reporting_task"],
                row["layer1_label"],
                *[row["models"][label]["layer1"]["display"] for label in labels],
            ])
        lines.append(markdown_table(["Reporting task", "指标", *labels], table_rows))

    lines.extend([
        "",
        "### Layer 1 逐任务最优结果",
        "",
        "该表只标记每个 reporting task 在主指标上的最优模型。",
        "",
        markdown_table(["任务族", "Reporting task", "指标", "最优模型"], layer1_best_rows(result)),
    ])

    lines.extend(["", "## 5. Layer 2：模板依从与内部自洽（State Score）"])
    for family, rows in rows_by_family(result).items():
        lines.extend(["", f"### {family}", ""])
        table_rows = []
        for row in rows:
            table_rows.append([
                row["reporting_task"],
                *[format_float(row["models"][label]["layer2_state_score"], 3) for label in labels],
            ])
        lines.append(markdown_table(["Reporting task", *labels], table_rows))

    lines.extend([
        "",
        "### Layer 2 概览",
        "",
        "以下为按 18 个 reporting tasks 等权平均的阅读辅助，不作为论文主指标。整体上，多数模型 Layer 2 接近 1，说明当前结构化模板较容易被模型遵循；因此论文中需要用 Layer 3 区分真正的推理步骤正确性。",
        "",
        markdown_table(["模型", "Layer 2 等权均值"], layer2_overview),
    ])

    lines.extend(["", "## 6. Layer 3：步骤级推理正确性", "", "MolEdit/MolUnd/RxnPred 使用 `Type I all-pass / Type II all-match`；MolOpt 使用 `Avg Step Score`。"])
    for family, rows in rows_by_family(result).items():
        lines.extend(["", f"### {family}", ""])
        table_rows = []
        for row in rows:
            metric = "Avg Step" if family == "MolOpt" else "Type I / Type II"
            table_rows.append([
                row["reporting_task"],
                metric,
                *[row["models"][label]["layer3"]["display"] for label in labels],
            ])
        lines.append(markdown_table(["Reporting task", "指标", *labels], table_rows))

    lines.extend([
        "",
        "### Layer 3 任务族概览",
        "",
        "以下同样是按 reporting tasks 等权平均的阅读辅助，不替代逐任务表。它能反映一个重要现象：Layer 2 普遍很高时，Layer 3 仍然存在明显模型差异，说明 step-wise formal CoT 评测提供了额外区分度。",
        "",
        markdown_table(["任务族", "模型", "指标", "等权均值"], layer3_overview),
    ])

    lines.extend(["", "## 7. 对比实验：Direct vs Template vs Template+Partial GT", "", "该实验来自 `results/ablation/run_all/{direct,template,template_gt}/deepseek-v3.2/`，只作为 prompt ablation，模型固定为 `deepseek-v3.2`，只比较 Layer 1。正文建议保留 MolUnd 和 MolOpt 两个任务族。"])
    for task_name, task_rows in ablation["tables"].items():
        lines.extend(["", f"### {task_name}", ""])
        lines.append(markdown_table(
            ["子任务", "主指标", "direct", "template", "template_gt"],
            [[r["subtask"], r["metric"], r["direct"], r["template"], r["template_gt"]] for r in task_rows],
        ))
    lines.extend(["", "### Family-Level 趋势", ""])
    lines.append(markdown_table(
        ["任务族", "direct", "template", "template_gt", "口径"],
        [[r["task"], r["direct"], r["template"], r["template_gt"], r["note"]] for r in ablation["family_level"]],
    ))

    lines.extend([
        "",
        "## 8. 主要观察",
        "",
        "- Gemini-3.1 在 Layer 1 的多项最终答案指标上最强，尤其是 MolEdit 三个任务、MolUnd 的 Ring Count/Murcko/Ring-System、RxnPred 四个 reporting tasks 以及 MolOpt PhysChem-Single。",
        "- Claude-Sonnet 在 MolUnd 的 SMILES Equivalence、MolOpt BioTarget-Single 和 PhysChem-Dual 上取得最优；在 yield prediction 的 MAE 上也最低。",
        "- GLM-5.1 在 Functional Group MAE 上最好，并在 Condition Ranking 的 Top-1 上最高，但其 Yield MAE 并不是最优。",
        "- Layer 2 整体接近饱和：Qwen3.5+、GPT-5.2、Gemini-3.1、Claude-Sonnet 的等权均值均在 0.99 左右。这说明结构化输出约束有效，但 Layer 2 不足以单独衡量推理质量。",
        "- Layer 3 与 Layer 1 不完全一致。例如部分模型最终答案可以较高，但 step-wise `Type I/Type II` 并不总是同步提升；这正是三层评估框架的必要性。",
        "- MolOpt 双目标任务整体仍较难，Dual-SR 明显低于单目标 SR。BioTarget-Dual 最高也只有 10.0，PhysChem-Dual 最高为 16.0。",
        "- 对比实验显示 template 相比 direct 在 MolOpt 上有明显提升；template_gt 继续小幅提升整体 family-level 均值。MolUnd 中 template_gt 对 Ring-System Scaffold 和 SMILES Equivalence 提升极大，但 Ring Count 的 MAE 没有改善，说明 partial GT 注入并非对所有子任务同向有效。",
        "",
        "## 9. 读表注意事项",
        "",
        "- 18 个 reporting tasks = MolEdit 3 + MolUnd 5 + RxnPred 6 + MolOpt 4。",
        "- Reporting task 只是论文展示标签，不改变底层 31 个 implementation subtasks 或任何 benchmark 样本。",
        "- 聚合项按 active 样本数加权平均；单子任务 reporting task 等同于原子任务结果。",
        "- `Layer 2` 高只说明模板填写与内部自洽强；`Layer 3` 才反映 formal CoT / PRM GT 对齐的步骤正确性。",
        "- `Condition Ranking` 和 `Yield Prediction` 已拆分，确保每个 reporting task 的 Layer 1 只有一个主指标。",
    ])
    return "\n".join(lines) + "\n"


def load_ablation_rows(task: str, arm: str) -> dict[str, dict[str, Any]]:
    path = PROJECT_ROOT / "results" / "ablation" / "run_all" / arm / "deepseek-v3.2" / f"{task}.summary.json"
    data = load_json(path)
    return {row["subtask"]: row for row in data["rows"]}


def format_ablation_value(metric: str, value: float | None) -> str:
    if value is None:
        return "-"
    if metric in {"sr_pct", "dual_sr_pct"}:
        return f"{value:.2f}"
    if metric == "mean_mae":
        return f"{value:.4f}"
    if metric in {"avg_tanimoto", "exact_match_acc"}:
        return f"{value:.4f}"
    return format_float(value, 4)


def compute_ablation() -> dict[str, Any]:
    arms = ["direct", "template", "template_gt"]
    tables = {}
    family_level = []
    for task, subtask_metrics in ABLATION_TASKS.items():
        arm_rows = {arm: load_ablation_rows(task, arm) for arm in arms}
        table = []
        normalized_scores = {arm: [] for arm in arms}
        raw_values = {arm: [] for arm in arms}
        for subtask, metric in subtask_metrics:
            item = {"subtask": subtask, "metric": metric}
            for arm in arms:
                row = arm_rows[arm][subtask]
                key = f"layer1_{metric}"
                value = row.get(key)
                item[arm] = format_ablation_value(metric, value)
                if value is not None:
                    raw_values[arm].append(float(value))
                    normalized_scores[arm].append(-float(value) if metric == "mean_mae" else float(value))
            table.append(item)
        tables["MolUnd" if task == "mol_und" else "MolOpt"] = table
        if task == "mol_und":
            scores = {arm: sum(normalized_scores[arm]) / len(normalized_scores[arm]) for arm in arms}
            family_level.append({
                "task": "MolUnd",
                "direct": f"{scores['direct']:.4f}",
                "template": f"{scores['template']:.4f}",
                "template_gt": f"{scores['template_gt']:.4f}",
                "note": "higher-better normalized; MAE negated",
            })
        else:
            scores = {arm: sum(raw_values[arm]) / len(raw_values[arm]) for arm in arms}
            family_level.append({
                "task": "MolOpt",
                "direct": f"{scores['direct']:.4f}",
                "template": f"{scores['template']:.4f}",
                "template_gt": f"{scores['template_gt']:.4f}",
                "note": "raw mean over SR/Dual-SR percentages",
            })
    return {"tables": tables, "family_level": family_level}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--doc-path", type=Path, default=PROJECT_ROOT / "docs" / "模型评测结果汇总.md")
    parser.add_argument("--no-doc", action="store_true", help="Do not update docs/模型评测结果汇总.md")
    args = parser.parse_args()

    result = compute_reporting_results(MODELS)
    ablation = compute_ablation()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    save_json(result, args.out_dir / "reporting_tasks_18.json")
    save_json(ablation, args.out_dir / "ablation_layer1.json")
    write_csvs(result, args.out_dir)
    markdown = build_main_markdown(result, ablation)
    (args.out_dir / "reporting_tasks_18.md").write_text(markdown, encoding="utf-8")
    if not args.no_doc:
        args.doc_path.write_text(markdown, encoding="utf-8")

    print(f"Wrote {args.out_dir / 'reporting_tasks_18.json'}")
    print(f"Wrote {args.out_dir / 'layer1.csv'}")
    print(f"Wrote {args.out_dir / 'layer2.csv'}")
    print(f"Wrote {args.out_dir / 'layer3.csv'}")
    if not args.no_doc:
        print(f"Updated {args.doc_path}")


if __name__ == "__main__":
    main()
