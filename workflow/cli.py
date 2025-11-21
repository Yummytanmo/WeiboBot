#!/usr/bin/env python3
"""Command-line runner for LangGraph workflows."""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from workflow import (  # noqa: E402
    LANGGRAPH_AVAILABLE,
    create_browse_interaction_graph,
    create_daily_agent_graph,
    create_daily_schedule_graph,
    create_post_review_graph,
    run_graph,
)


DEFAULTS = {
    "llm_model": "gpt-4o-mini",
    "llm_temperature": 0.3,
    "tool_timeout": 600.0,
    "current_post_topic": None,
    "current_post_notes": None,
    "max_review_rounds": 2,
    "auto_post": True,
    "min_slots": 3,
    "max_slots": 5,
    "start_time": "09:00",
    "end_time": "22:00",
    "max_interactions": 5,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a workflow from the CLI (supports JSON/YAML config)."
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to a JSON/YAML config file containing workflow settings.",
    )
    parser.add_argument(
        "--workflow",
        choices=["daily_schedule", "post_review", "browse_interaction", "daily_agent"],
        help="Workflow name (overrides config).",
    )
    parser.add_argument("--agent-id", help="Weibo agent/account ID (overrides config).")
    parser.add_argument("--llm-model", help="LLM model name.")
    parser.add_argument("--llm-temperature", type=float, help="LLM temperature.")
    parser.add_argument("--tool-timeout", type=float, help="Tool timeout in seconds.")

    # Post-related
    parser.add_argument("--current-post-topic", help="Topic for post_review/daily_agent.")
    parser.add_argument("--current-post-notes", help="Notes for post_review/daily_agent.")
    parser.add_argument("--max-review-rounds", type=int, help="Max review rounds.")
    parser.add_argument(
        "--auto-post",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Whether to auto post after review.",
    )

    # Schedule-related
    parser.add_argument("--min-slots", type=int, help="Minimum schedule items.")
    parser.add_argument("--max-slots", type=int, help="Maximum schedule items.")
    parser.add_argument("--start-time", help="Schedule start time (HH:MM).")
    parser.add_argument("--end-time", help="Schedule end time (HH:MM).")

    # Browse-related
    parser.add_argument("--max-interactions", type=int, help="Maximum interactions for browse.")

    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Print full final state as JSON (default prints a compact summary).",
    )

    return parser.parse_args()


def _get_graph(name: str):
    graphs = {
        "daily_schedule": create_daily_schedule_graph,
        "post_review": create_post_review_graph,
        "browse_interaction": create_browse_interaction_graph,
        "daily_agent": create_daily_agent_graph,
    }
    if name not in graphs:
        raise ValueError(f"Unknown workflow: {name}")
    return graphs[name]()


def _load_config(path: Path) -> Dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # noqa: BLE001
            raise RuntimeError("pyyaml is required for YAML config. pip install pyyaml") from exc
        data = yaml.safe_load(content)
    else:
        data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a top-level object/dict.")
    return data


def _merge_config(args: argparse.Namespace) -> Dict[str, Any]:
    # Load config if provided.
    config_data: Dict[str, Any] = {}
    if args.config:
        if not args.config.exists():
            raise FileNotFoundError(f"Config file not found: {args.config}")
        config_data = _load_config(args.config)

    # CLI overrides config only when explicitly provided (argparse gives None when not passed).
    cli_overrides = {
        k: v
        for k, v in vars(args).items()
        if k not in {"config", "json_output"} and v is not None
    }

    merged = {**config_data, **cli_overrides}

    # Apply defaults where missing.
    for key, val in DEFAULTS.items():
        merged.setdefault(key, val)

    # Required checks
    if not merged.get("workflow"):
        raise ValueError("workflow is required (set in config or with --workflow).")
    if not merged.get("agent_id"):
        raise ValueError("agent_id is required (set in config or with --agent-id).")

    return merged


def main() -> int:
    args = _parse_args()

    if not LANGGRAPH_AVAILABLE:
        sys.stderr.write("LangGraph not installed. Please run: pip install langgraph langchain langchain-openai\n")
        return 1

    try:
        merged = _merge_config(args)
        graph = _get_graph(merged["workflow"])
        initial_state = {
            "agent_id": merged["agent_id"],
            "llm_model": merged["llm_model"],
            "llm_temperature": merged["llm_temperature"],
            "tool_timeout": merged["tool_timeout"],
            "current_post_topic": merged.get("current_post_topic"),
            "current_post_notes": merged.get("current_post_notes"),
            "max_review_rounds": merged.get("max_review_rounds"),
            "auto_post": merged.get("auto_post"),
            "min_slots": merged.get("min_slots"),
            "max_slots": merged.get("max_slots"),
            "start_time": merged.get("start_time"),
            "end_time": merged.get("end_time"),
            "max_interactions": merged.get("max_interactions"),
        }
        final_state = run_graph(graph, initial_state)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Workflow failed: {exc}\n")
        return 1

    if args.json_output:
        print(json.dumps(final_state, ensure_ascii=False, indent=2))
    else:
        summary = {
            "workflow": args.workflow,
            "current_node": final_state.get("current_node"),
            "review_round": final_state.get("review_round"),
            "posts": final_state.get("posts"),
            "schedule_items": final_state.get("schedule_items"),
            "interactions": final_state.get("interactions"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
