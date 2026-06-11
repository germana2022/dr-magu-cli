from __future__ import annotations

from pathlib import Path

from dr_magu.agents.runner import AgentRunner
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.skills.runtime import SkillRuntime


def test_skill_runtime_lists_and_shows_default_skills(tmp_path: Path):
    runtime = SkillRuntime(tmp_path)

    listed = runtime.list_skills()
    assert listed.success is True
    skill_ids = {skill["id"] for skill in listed.data["skills"]}
    assert {"research", "filesystem", "github", "documentation", "architecture", "code-review", "report"}.issubset(skill_ids)

    shown = runtime.show_skill("research")
    assert shown.success is True
    assert "research" in shown.data["skill"]["capabilities"]


def test_agent_skill_attach_detach_and_aggregate(tmp_path: Path):
    agent_runner = AgentRunner(tmp_path)
    assert agent_runner.create_agent("researcher", role="researcher", workflow="research-brief").success

    skills = SkillRuntime(tmp_path)
    attached = skills.attach("researcher", "filesystem")
    assert attached.success is True
    assert "filesystem" in attached.data["skills"]

    agent_skills = skills.agent_skills("researcher")
    assert agent_skills.success is True
    assert "filesystem" in agent_skills.data["skill_ids"]
    assert "files_read" in agent_skills.data["aggregate"]["capabilities"]
    assert (tmp_path / ".dr-magu" / "skills" / "agent_skills.yaml").exists()

    detached = skills.detach("researcher", "filesystem")
    assert detached.success is True
    assert "filesystem" not in detached.data["skills"]


def test_command_processor_supports_agent_skill_commands(tmp_path: Path):
    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config={})
    processor = CommandProcessor(registry)

    assert processor.execute_line("agent create researcher --role researcher --workflow research-brief", context).success
    assert processor.execute_line("skill list", context).success
    assert processor.execute_line("skill show research", context).success
    assert processor.execute_line("skill attach researcher filesystem", context).success
    agent_skills = processor.execute_line("agent skills researcher", context)
    assert agent_skills.success is True
    assert "filesystem" in agent_skills.data["skill_ids"]
    assert processor.execute_line("skill detach researcher filesystem", context).success
