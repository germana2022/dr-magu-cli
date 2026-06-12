import json
from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.multi_agent.team import TeamRuntime


def test_team_run_persists_collaboration_artifacts(tmp_path):
    runtime = TeamRuntime(tmp_path)
    assert runtime.create("repo-analysis").success
    assert runtime.agent_runner.create_agent("researcher", role="researcher", workflow="research-brief").success
    assert runtime.agent_runner.create_agent("architect", role="architect", workflow="research-brief").success
    assert runtime.agent_runner.create_agent("reviewer", role="reviewer", workflow="research-brief").success
    assert runtime.agent_runner.create_agent("reporter", role="reporter", workflow="research-brief").success
    for agent_id in ["researcher", "architect", "reviewer", "reporter"]:
        assert runtime.add("repo-analysis", agent_id).success

    result = runtime.run("repo-analysis", "Analyze this repository", dry_run=True)

    assert result.success is True
    manifest = result.data["artifact_manifest"]
    assert manifest["artifact_count"] == 5
    assert Path(manifest["path"]).exists()
    artifact_dir = Path(result.data["artifact_dir"])
    assert (artifact_dir / "01-researcher-repository-findings.md").exists()
    assert (artifact_dir / "02-architect-architecture.md").exists()
    assert (artifact_dir / "03-reviewer-review.md").exists()
    assert (artifact_dir / "04-reporter-final-report.md").exists()

    architect_prompt = result.data["team_run"]["results"][1]["prompt"]
    assert "Artifacts available to consume" in architect_prompt
    assert "Repository Findings" in architect_prompt


def test_team_artifacts_command_lists_manifest(tmp_path):
    runtime = TeamRuntime(tmp_path)
    assert runtime.create("repo-analysis").success
    assert runtime.agent_runner.create_agent("researcher", role="researcher", workflow="research-brief").success
    assert runtime.add("repo-analysis", "researcher").success
    run = runtime.run("repo-analysis", "Analyze this repository", dry_run=True)
    run_id = run.data["team_run"]["run_id"]

    context = CommandContext(workspace_path=str(tmp_path), output_format="human", config=load_config())
    listed = CommandProcessor(registry).execute_line(f"team artifacts {run_id}", context)

    assert listed.success is True
    assert listed.tool == "team.artifacts"
    assert listed.data["run_id"] == run_id
    assert listed.data["artifact_count"] == 2
