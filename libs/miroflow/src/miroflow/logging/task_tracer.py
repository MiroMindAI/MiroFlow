# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from omegaconf import DictConfig
from pydantic import BaseModel, Field

from .logger import bootstrap_logger

logger = bootstrap_logger()


class StepRecord(BaseModel):
    """Record detailed information of task execution steps"""

    step_name: str
    message: str
    timestamp: datetime
    status: Literal["info", "warning", "failed", "success", "debug"] = "info"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskTracer(BaseModel):
    """Only use primitive types, datatime, Path etc."""

    status: Literal["pending", "running", "completed", "interrupted", "failed"] = (
        "pending"
    )

    # task info. hydrated BEFORE task execution.
    task_id: str = ""
    task_name: str = ""
    task_file_name: str | None = ""
    ground_truth: str | None
    input: Any = None

    # not task-related info. hydrated BEFORE task execution.
    log_path: Path
    env_info: dict[str, Any] = Field(
        default_factory=dict
    )  # populate by `def env_info()`.
    trace_data: dict[str, Any] = Field(
        default_factory=dict
    )  # populate by `def process_span_for_summary()`.

    # profile exeuction time. hydrated AFTER task execution.
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: datetime = Field(default_factory=datetime.now)

    # record task result. hydrdrated AFTER task execution.
    final_boxed_answer: str = ""
    llm_as_judge_result: str = ""
    error: str = ""

    # record task exection detail. hydrated DURING task_execution.
    current_main_turn_id: int = 0
    current_sub_agent_turn_id: int = 0
    sub_agent_counter: int = 0
    current_sub_agent_session_id: str | None = None
    main_agent_message_history: dict[str, Any] = Field(default_factory=dict)
    sub_agent_message_history_sessions: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )
    step_logs: list[StepRecord] = Field(default_factory=list)

    def start_sub_agent_session(
        self, sub_agent_name: str, subtask_description: str
    ) -> str:
        """Start a new sub-agent session"""
        self.sub_agent_counter += 1
        session_id = f"{sub_agent_name}_{self.sub_agent_counter}"
        self.current_sub_agent_session_id = session_id

        # record sub-agent session start
        self.log_step(
            f"sub_{sub_agent_name}_session_start",
            f"Starting {session_id} for subtask: {subtask_description[:100]}{'...' if len(subtask_description) > 100 else ''}",
            "info",
            metadata={"session_id": session_id, "subtask": subtask_description},
        )

        return session_id

    def end_sub_agent_session(self, sub_agent_name: str):
        """End the current sub-agent session"""
        self.log_step(
            f"sub_{sub_agent_name}_session_end",
            f"Ending {self.current_sub_agent_session_id}",
            "success",
            metadata={"session_id": self.current_sub_agent_session_id},
        )
        self.current_sub_agent_session_id = None
        return None

    def log_step(
        self,
        step_name: str,
        message: str,
        status: Literal["info", "warning", "failed", "success", "debug"] = "info",
        metadata: dict[str, Any] | None = None,
    ):
        """Record execution step"""
        step_log = StepRecord(
            step_name=step_name,
            message=message,
            timestamp=datetime.now(),
            status=status,
            metadata=metadata or {},
        )
        self.step_logs.append(step_log)
        # Also print to console
        logger.debug(f"{step_name}: {message}")

    def save(self):
        """Persist TaskTracer to disk. used in a finally block, thus never raise Exception."""
        try:
            if not self.log_path.exists():
                self.log_path.parent.mkdir(exist_ok=True, parents=True)
            with open(self.log_path, mode="w") as dest:
                dest.write(self.model_dump_json(indent=2))
        except Exception as e:
            logger.error(e, stack_info=True, exc_info=True)


def env_info(cfg: DictConfig) -> dict:
    """Record the environment in the trace. This hydrdates `TaskTracer.env_info`."""

    # keys from environment
    SERPER_API_KEY = cfg.env.serper_api_key
    JINA_API_KEY = cfg.env.jina_api_key
    ANTHROPIC_API_KEY = cfg.env.anthropic_api_key
    OPENAI_API_KEY = cfg.env.openai_api_key
    NEWAPI_API_KEY = cfg.env.newapi_api_key
    E2B_API_KEY = cfg.env.e2b_api_key
    HTTPS_PROXY = cfg.env.https_proxy
    GEMINI_API_KEY = cfg.env.gemini_api_key
    OPENROUTER_API_KEY = cfg.env.openrouter_api_key

    return {
        # LLM Configuration
        "llm_provider": cfg.llm.provider,
        "llm_model_name": cfg.llm.model_name,
        "llm_temperature": cfg.llm.temperature,
        "llm_top_p": cfg.llm.top_p,
        "llm_min_p": cfg.llm.min_p,
        "llm_top_k": cfg.llm.top_k,
        "llm_max_tokens": cfg.llm.max_tokens,
        "llm_async_client": cfg.llm.async_client,
        "keep_tool_result": cfg.llm.keep_tool_result,
        "oai_tool_thinking": cfg.llm.oai_tool_thinking,
        # Agent Configuration
        "main_agent_max_turns": cfg.agent.main_agent.max_turns,
        **{
            f"sub_{sub_agent}_max_turns": cfg.agent.sub_agents[sub_agent].max_turns
            for sub_agent in cfg.agent.sub_agents
        },
        # use https proxy
        "https_proxy": HTTPS_PROXY,
        # Third Party API Keys (masked for security)
        "has_serper_api_key": bool(SERPER_API_KEY),
        "has_jina_api_key": bool(JINA_API_KEY),
        "has_e2b_api_key": bool(E2B_API_KEY),
        # LLM API Keys
        "has_gemini_api_key": bool(GEMINI_API_KEY),
        "has_anthropic_api_key": bool(ANTHROPIC_API_KEY),
        "has_newapi_api_key": bool(NEWAPI_API_KEY),
        "has_openai_api_key": bool(OPENAI_API_KEY),
        "has_openrouter_api_key": bool(OPENROUTER_API_KEY),
        # Base URLs
        "anthropic_base_url": cfg.env.anthropic_base_url,
        "openai_base_url": cfg.env.openai_base_url,
        "newapi_base_url": cfg.env.newapi_base_url,
        "openrouter_base_url": cfg.env.openrouter_base_url,
    }


def process_spans_for_summary(trace_obj: Any, cfg: DictConfig):
    """
    Processes span-data for performance profile. This hydrates `TaskTracer.trace_data`.
    """
    # --- 1. Pre-computation and tree building ---
    spans_by_id = {span.span_id: span for span in getattr(trace_obj, "spans", [])}
    children_by_parent_id = defaultdict(list)
    for span in spans_by_id.values():
        children_by_parent_id[span.parent_id].append(span)

    def get_sub_agent_spans(
        sub_agent_name: str,
        spans_by_id: dict[str, Any],
        children_by_parent_id: dict[str, list[Any]],
    ) -> set[str]:
        # --- 2. Find all sub-agent spans ---
        sub_agent_span_ids = set()
        queue = []
        # Find the root sub-agent spans and use them as the entry point for the search
        for span in spans_by_id.values():
            span_name = getattr(span.span_data, "name", "")
            if sub_agent_name in span_name:
                # The children of this span belong to the sub-agent's context
                queue.extend(children_by_parent_id.get(span.span_id, []))

        # Start the BFS to find all descendant spans
        head = 0
        while head < len(queue):
            current_span = queue[head]
            head += 1
            if current_span.span_id not in sub_agent_span_ids:
                sub_agent_span_ids.add(current_span.span_id)
                queue.extend(children_by_parent_id.get(current_span.span_id, []))

        return sub_agent_span_ids

    sub_agent_span_ids_dict = {
        sub_agent_name: get_sub_agent_spans(
            sub_agent_name, spans_by_id, children_by_parent_id
        )
        for sub_agent_name in cfg.agent.sub_agents.keys()
    }

    # --- 3. Pre-calculate all span durations ---
    for span in spans_by_id.values():
        duration = (
            datetime.fromisoformat(span.ended_at)
            - datetime.fromisoformat(span.started_at)
        ).total_seconds()
        span.duration = duration  # Attach for later use

    # --- 4. Final Wall Time Calculations ---
    wall_time_total = 0
    if hasattr(trace_obj, "started_at") and hasattr(trace_obj, "ended_at"):
        wall_time_total = (
            datetime.fromisoformat(trace_obj.ended_at)
            - datetime.fromisoformat(trace_obj.started_at)
        ).total_seconds()

    # Find top-level spans for main agent and all sub-agent root spans
    main_agent_top_level_spans = [
        s
        for s in spans_by_id.values()
        if s.parent_id is None
        and not any(
            sub_agent_name in getattr(s.span_data, "name", "")
            for sub_agent_name in cfg.agent.sub_agents.keys()
        )
    ]
    sub_agent_root_spans_dict = {
        sub_agent_name: [
            s
            for s in spans_by_id.values()
            if s.parent_id is None
            and sub_agent_name in getattr(s.span_data, "name", "")
        ]
        for sub_agent_name in cfg.agent.sub_agents.keys()
    }

    # Calculate main agent wall time
    wall_time_main_agent_llm = sum(
        s.duration
        for s in main_agent_top_level_spans
        if getattr(s.span_data, "name", "generation_span") == "generation_span"
    )
    wall_time_main_agent_tool = sum(
        s.duration
        for s in main_agent_top_level_spans
        if getattr(s.span_data, "name", "generation_span") != "generation_span"
    )
    wall_time_main_agent = wall_time_main_agent_llm + wall_time_main_agent_tool

    # Calculate sub-agent wall time and its internal breakdown
    def calculate_sub_agent_wall_time(
        sub_agent_name: str,
    ) -> tuple[float, float, float]:
        wall_time_sub_agent = sum(
            s.duration for s in sub_agent_root_spans_dict[sub_agent_name]
        )
        wall_time_sub_agent_llm = 0
        wall_time_sub_agent_tool = 0
        for root_span in sub_agent_root_spans_dict[sub_agent_name]:
            sub_agent_children = children_by_parent_id.get(root_span.span_id, [])
            wall_time_sub_agent_llm += sum(
                s.duration
                for s in sub_agent_children
                if getattr(s.span_data, "name", "generation_span") == "generation_span"
            )
            wall_time_sub_agent_tool += sum(
                s.duration
                for s in sub_agent_children
                if getattr(s.span_data, "name", "generation_span") != "generation_span"
            )
        return wall_time_sub_agent, wall_time_sub_agent_llm, wall_time_sub_agent_tool

    wall_time_sub_agent_dict = {
        sub_agent_name: calculate_sub_agent_wall_time(sub_agent_name)
        for sub_agent_name in cfg.agent.sub_agents.keys()
    }

    # Calculate total wall times for summary
    wall_time_llm = wall_time_main_agent_llm + sum(
        wall_time_sub_agent_dict[sub_agent_name][1]
        for sub_agent_name in cfg.agent.sub_agents.keys()
    )
    wall_time_tool = wall_time_main_agent_tool + sum(
        wall_time_sub_agent_dict[sub_agent_name][2]
        for sub_agent_name in cfg.agent.sub_agents.keys()
    )

    # Orchestration breakdown
    orchestration_sub_agent_dict = {
        sub_agent_name: wall_time_sub_agent_dict[sub_agent_name][0]
        - (
            wall_time_sub_agent_dict[sub_agent_name][1]
            + wall_time_sub_agent_dict[sub_agent_name][2]
        )
        for sub_agent_name in cfg.agent.sub_agents.keys()
    }

    orchestration_main_agent = (
        wall_time_total
        - wall_time_main_agent
        - sum(
            wall_time_sub_agent_dict[sub_agent_name][0]
            for sub_agent_name in cfg.agent.sub_agents.keys()
        )
    )
    orchestration_total = orchestration_main_agent + sum(
        orchestration_sub_agent_dict.values()
    )

    # --- 5. Tool Workload Breakdown ---
    tool_workload_breakdown = defaultdict(float)
    function_spans = [
        s
        for s in spans_by_id.values()
        if getattr(s.span_data, "name", "generation_span") != "generation_span"
        and "agent-" not in getattr(s.span_data, "name", "generation_span")
    ]
    for span in function_spans:
        tool_workload_breakdown[getattr(span.span_data, "name")] += span.duration

    return {
        "trace_id": trace_obj.trace_id,
        "workflow_name": trace_obj.name,
        "performance_summary": {
            "total_wall_time": wall_time_total,
            "primary_breakdown": {
                "main-agent": {
                    "total": wall_time_main_agent + orchestration_main_agent,
                    "llm": wall_time_main_agent_llm,
                    "tool": wall_time_main_agent_tool,
                    "orchestration": orchestration_main_agent,
                },
                **{
                    sub_agent_name: {
                        "total": wall_time_sub_agent_dict[sub_agent_name][0],
                        "llm": wall_time_sub_agent_dict[sub_agent_name][1],
                        "tool": wall_time_sub_agent_dict[sub_agent_name][2],
                        "orchestration": orchestration_sub_agent_dict[sub_agent_name],
                    }
                    for sub_agent_name in cfg.agent.sub_agents.keys()
                },
            },
            "cross_cutting_breakdown": {
                "total_llm_time": wall_time_llm,
                "total_tool_time": wall_time_tool,
                "total_orchestration_time": orchestration_total,
            },
        },
        "tool_workload_breakdown": dict(tool_workload_breakdown),
        "spans": [
            {
                "name": getattr(s.span_data, "name", "generation_span"),
                "agent_context": "main-agent"
                if s.parent_id is None
                else next(
                    (
                        sub_agent_name
                        for sub_agent_name in cfg.agent.sub_agents.keys()
                        if s.span_id in sub_agent_span_ids_dict[sub_agent_name]
                    ),
                    "main-agent",
                ),
                "duration_seconds": s.duration,
                "start_time": s.started_at,
                "end_time": s.ended_at,
            }
            for s in spans_by_id.values()
        ],
    }
