from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from dr_magu.project_context.generator import generate_project_context
from dr_magu.result import ToolResult
from dr_magu.scanner.models import RepositoryScan
from dr_magu.scanner.repository_scanner import scan_repository
from dr_magu.scanner.writers import write_latest_scan
from dr_magu.workflows.models import RepositoryContextWorkflowState, WorkflowEvent
from dr_magu.workflows.store import WorkflowRunStore

WORKFLOW_NAME = "repository.context"


def run_repository_context_workflow(
    workspace_path: str,
    run_id: str,
    store: WorkflowRunStore,
    session_id: str | None = None,
) -> ToolResult:
    """Run the deterministic repository.context workflow.

    The workflow uses LangGraph when the dependency is available. A deterministic
    fallback is kept so local development and tests can run without external model
    providers or network access. No LLM is used in either path.
    """
    try:
        return _run_with_langgraph(workspace_path, run_id, store, session_id)
    except ModuleNotFoundError:
        return _run_deterministic(workspace_path, run_id, store, session_id)


def _run_with_langgraph(
    workspace_path: str,
    run_id: str,
    store: WorkflowRunStore,
    session_id: str | None,
) -> ToolResult:
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(dict)

    def load_session(state: dict[str, Any]) -> dict[str, Any]:
        return _timed_node(store, run_id, "load_session", lambda: state)

    def run_scan(state: dict[str, Any]) -> dict[str, Any]:
        def work() -> dict[str, Any]:
            scan_result = scan_repository(workspace_path)
            if not scan_result.success or not scan_result.data:
                state.setdefault("errors", []).extend(scan_result.errors or ["Repository scan failed."])
                return state
            scan = RepositoryScan.model_validate(scan_result.data)
            scan_path = write_latest_scan(workspace_path, scan)
            state["scan_path"] = str(scan_path)
            return state

        return _timed_node(store, run_id, "run_scan", work)

    def generate_context(state: dict[str, Any]) -> dict[str, Any]:
        def work() -> dict[str, Any]:
            context_result = generate_project_context(workspace_path, refresh=False)
            if not context_result.success or not context_result.data:
                state.setdefault("errors", []).extend(context_result.errors or ["Context generation failed."])
                return state
            data = context_result.data
            state["context_path"] = str(data.get("context_dir", ""))
            state["generated_files"] = [item.get("path", "") for item in data.get("generated_files", []) if isinstance(item, dict)]
            return state

        return _timed_node(store, run_id, "generate_context", work)

    def summarize_outputs(state: dict[str, Any]) -> dict[str, Any]:
        return _timed_node(store, run_id, "summarize_outputs", lambda: state)

    graph.add_node("load_session", load_session)
    graph.add_node("run_scan", run_scan)
    graph.add_node("generate_context", generate_context)
    graph.add_node("summarize_outputs", summarize_outputs)
    graph.add_edge(START, "load_session")
    graph.add_edge("load_session", "run_scan")
    graph.add_edge("run_scan", "generate_context")
    graph.add_edge("generate_context", "summarize_outputs")
    graph.add_edge("summarize_outputs", END)

    initial_state = RepositoryContextWorkflowState(workspace_path=str(Path(workspace_path).resolve()), session_id=session_id).model_dump()
    final_state = graph.compile().invoke(initial_state)
    return _final_result(final_state, run_id)


def _run_deterministic(
    workspace_path: str,
    run_id: str,
    store: WorkflowRunStore,
    session_id: str | None,
) -> ToolResult:
    state = RepositoryContextWorkflowState(workspace_path=str(Path(workspace_path).resolve()), session_id=session_id).model_dump()

    def scan_work() -> dict[str, Any]:
        scan_result = scan_repository(workspace_path)
        if not scan_result.success or not scan_result.data:
            state["errors"] = scan_result.errors or ["Repository scan failed."]
            return state
        scan = RepositoryScan.model_validate(scan_result.data)
        state["scan_path"] = str(write_latest_scan(workspace_path, scan))
        return state

    state = _timed_node(store, run_id, "run_scan", scan_work)
    if state.get("errors"):
        return _final_result(state, run_id)

    def context_work() -> dict[str, Any]:
        context_result = generate_project_context(workspace_path, refresh=False)
        if not context_result.success or not context_result.data:
            state["errors"] = context_result.errors or ["Context generation failed."]
            return state
        state["context_path"] = str(context_result.data.get("context_dir", ""))
        state["generated_files"] = [
            item.get("path", "")
            for item in context_result.data.get("generated_files", [])
            if isinstance(item, dict)
        ]
        return state

    state = _timed_node(store, run_id, "generate_context", context_work)
    if state.get("errors"):
        return _final_result(state, run_id)

    state = _timed_node(store, run_id, "summarize_outputs", lambda: state)
    return _final_result(state, run_id)


def _final_result(state: dict[str, Any], run_id: str) -> ToolResult:
    errors = list(state.get("errors") or [])
    data = {
        "run_id": run_id,
        "workflow": WORKFLOW_NAME,
        "workspace_path": state.get("workspace_path"),
        "session_id": state.get("session_id"),
        "scan_path": state.get("scan_path"),
        "context_path": state.get("context_path"),
        "generated_files": state.get("generated_files", []),
        "errors": errors,
    }
    return ToolResult(success=not errors, tool="workflow.run", data=data, errors=errors)


def _timed_node(store: WorkflowRunStore, run_id: str, node: str, func: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    started = time.perf_counter()
    _event(store, run_id, "node.started", node)
    try:
        state = func()
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _event(store, run_id, "node.failed", node, message=str(exc), duration_ms=duration_ms)
        raise
    duration_ms = int((time.perf_counter() - started) * 1000)
    if state.get("errors"):
        _event(store, run_id, "node.failed", node, message="; ".join(state.get("errors", [])), duration_ms=duration_ms)
    else:
        _event(store, run_id, "node.completed", node, duration_ms=duration_ms)
    return state


def _event(
    store: WorkflowRunStore,
    run_id: str,
    event_type: str,
    node: str,
    message: str | None = None,
    duration_ms: int | None = None,
) -> None:
    store.append_event(
        run_id,
        WorkflowEvent(
            type=event_type,
            workflow=WORKFLOW_NAME,
            run_id=run_id,
            node=node,
            message=message,
            duration_ms=duration_ms,
        ),
    )
