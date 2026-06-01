"""Shared evaluation infrastructure."""

from .config import (
    TaskSpec,
    get_task_spec,
    resolve_dataset_name,
    resolve_gt_dataset_path,
    resolve_module_name,
    resolve_output_dir,
)
from .parser_adapter import ParserAdapter
from .runner import BaseRunner, RunnerConfig
from .sampler import run_sampling
from .utils import (
    COMMON_ID_FALLBACK_FIELDS,
    find_gt_record,
    resolve_record_id,
)

__all__ = [
    "BaseRunner",
    "COMMON_ID_FALLBACK_FIELDS",
    "find_gt_record",
    "ParserAdapter",
    "resolve_record_id",
    "RunnerConfig",
    "TaskSpec",
    "get_task_spec",
    "resolve_dataset_name",
    "resolve_gt_dataset_path",
    "resolve_module_name",
    "resolve_output_dir",
    "run_sampling",
]
