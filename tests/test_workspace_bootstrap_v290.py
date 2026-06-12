from pathlib import Path

from typer.testing import CliRunner

from dr_magu.bootstrap import WorkspaceBootstrap
from dr_magu.cli import app
from dr_magu.agents.runner import AgentRunner
from dr_magu.multi_agent.team import TeamRuntime
from dr_magu.workflow_engine.engine import WorkflowEngine


def test_workspace_init_creates_operational_defaults(tmp_path: Path):
    result = WorkspaceBootstrap(tmp_path).init()

    assert result.success, result.errors
    assert (tmp_path / '.dr-magu' / 'config' / 'mcp_servers.json').exists()
    assert (tmp_path / '.dr-magu' / 'agents' / 'agents.yaml').exists()
    assert (tmp_path / '.dr-magu' / 'skills' / 'agent_skills.yaml').exists()
    assert (tmp_path / '.dr-magu' / 'teams' / 'teams.yaml').exists()
    assert (tmp_path / '.dr-magu' / 'workflows' / 'repo-analysis.yaml').exists()
    assert (tmp_path / '.dr-magu' / 'bootstrap.json').exists()

    agents = AgentRunner(tmp_path).list_agents().data['agents']
    agent_ids = {agent['id'] for agent in agents}
    assert {'researcher', 'architect', 'reviewer', 'reporter'}.issubset(agent_ids)

    teams = TeamRuntime(tmp_path).list().data['teams']
    assert {'repo-analysis', 'research-team'}.issubset({team['id'] for team in teams})

    workflows = {workflow.id for workflow in WorkflowEngine(tmp_path).list_definitions()}
    assert {'research-brief', 'repository-context', 'repo-analysis', 'security-review'}.issubset(workflows)


def test_workspace_doctor_reports_bootstrap_health(tmp_path: Path):
    WorkspaceBootstrap(tmp_path).init()
    result = WorkspaceBootstrap(tmp_path).doctor()

    assert result.success, result.errors
    assert result.data['ok'] is True
    assert result.data['summary']['failed'] == 0


def test_cli_init_and_doctor(tmp_path: Path):
    runner = CliRunner()

    init = runner.invoke(app, ['init', '--workspace', str(tmp_path), '--json'])
    assert init.exit_code == 0, init.output
    assert 'workspace.init' in init.output

    doctor = runner.invoke(app, ['doctor', '--workspace', str(tmp_path), '--json'])
    assert doctor.exit_code == 0, doctor.output
    assert 'workspace.doctor' in doctor.output
