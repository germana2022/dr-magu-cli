from __future__ import annotations

import yaml

from dr_magu.agents.manager import AgentManager
from dr_magu.agents.registry import AgentRegistry
from dr_magu.agents.runner import AgentRunner
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry


def _write_agent_file(tmp_path, agent_id: str = "repository-health"):
    path = tmp_path / "agent.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "agents": {
                    agent_id: {
                        "name": "Repository Health",
                        "description": "Validate repository context generation.",
                        "role": "repository_health",
                        "workflow": "repository.context",
                        "enabled": True,
                        "deleted": False,
                        "requires_llm": False,
                        "capabilities": ["scan_repository", "generate_context"],
                        "aliases": ["repo-health"],
                        "model": {"provider": None, "base_url": None, "model": None, "temperature": None},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_agent_manager_adds_workspace_agent_from_file(tmp_path):
    agent_file = _write_agent_file(tmp_path)

    result = AgentManager(tmp_path).add_from_file(agent_file)

    assert result.success
    agent = AgentRegistry(tmp_path).get("repository-health")
    assert agent.id == "repository-health"
    assert agent.source == "workspace"
    assert agent.enabled is True


def test_agent_manager_disable_enable_and_soft_delete_agent(tmp_path):
    manager = AgentManager(tmp_path)
    agent_file = _write_agent_file(tmp_path)
    assert manager.add_from_file(agent_file).success

    disabled = manager.disable("repository-health")
    assert disabled.success
    assert AgentRegistry(tmp_path).get("repository-health").enabled is False

    enabled = manager.enable("repository-health")
    assert enabled.success
    assert AgentRegistry(tmp_path).get("repository-health").enabled is True

    deleted = manager.delete("repository-health")
    assert deleted.success
    assert AgentRegistry(tmp_path).get("repository-health", include_deleted=True).deleted is True


def test_deleted_agents_are_hidden_by_default(tmp_path):
    manager = AgentManager(tmp_path)
    agent_file = _write_agent_file(tmp_path)
    assert manager.add_from_file(agent_file).success
    assert manager.delete("repository-health").success

    visible = AgentRegistry(tmp_path).list()
    with_deleted = AgentRegistry(tmp_path).list(include_deleted=True)

    assert all(agent.id != "repository-health" for agent in visible)
    assert any(agent.id == "repository-health" for agent in with_deleted)


def test_agent_validation_detects_unknown_workflow(tmp_path):
    bad_file = _write_agent_file(tmp_path, agent_id="bad-agent")
    payload = yaml.safe_load(bad_file.read_text(encoding="utf-8"))
    payload["agents"]["bad-agent"]["workflow"] = "missing.workflow"
    bad_file.write_text(yaml.safe_dump(payload), encoding="utf-8")

    result = AgentManager(tmp_path).add_from_file(bad_file)

    assert not result.success
    assert "unknown workflow" in " ".join(result.errors)


def test_agent_runner_exposes_lifecycle_operations(tmp_path):
    runner = AgentRunner(tmp_path)
    agent_file = _write_agent_file(tmp_path)

    assert runner.add_agent_from_file(agent_file).success
    assert runner.validate_agent("repository-health").success
    assert runner.disable_agent("repository-health").success
    assert runner.enable_agent("repository-health").success
    assert runner.delete_agent("repository-health").success


def test_command_processor_supports_agent_lifecycle_commands(tmp_path):
    agent_file = _write_agent_file(tmp_path)
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    processor = CommandProcessor(registry)

    assert processor.execute_line(f"agent.add {agent_file}", context).success
    assert processor.execute_line("agent.validate repository-health", context).success
    assert processor.execute_line("agent.disable repository-health", context).success
    assert processor.execute_line("agent.enable repository-health", context).success
    assert processor.execute_line("agent.delete repository-health", context).success
