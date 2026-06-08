from dr_magu.brain.intent_models import (
    INTENT_DOCUMENT_ACTION,
    INTENT_GENERAL_CHAT,
    INTENT_RESEARCH_ACTION,
    INTENT_SCHEDULE_ACTION,
    INTENT_SOFTWARE_ACTION,
    INTENT_WORKSPACE_ACTION,
)
from dr_magu.brain.intent_router import classify_prompt
from dr_magu.brain.commands import brain_route


def test_routes_general_chat():
    result = classify_prompt("Who was Albert Einstein?")
    assert result.intent == INTENT_GENERAL_CHAT


def test_routes_workspace_action_in_spanish():
    result = classify_prompt("analiza este repositorio y genera contexto")
    assert result.intent in {INTENT_WORKSPACE_ACTION, INTENT_DOCUMENT_ACTION}


def test_routes_research_action():
    result = classify_prompt("search the web for five best websites about AI tools")
    assert result.intent == INTENT_RESEARCH_ACTION


def test_routes_document_action():
    result = classify_prompt("generate a PDF report from the research")
    assert result.intent == INTENT_DOCUMENT_ACTION


def test_routes_schedule_action():
    result = classify_prompt("schedule a daily background report")
    assert result.intent == INTENT_SCHEDULE_ACTION


def test_routes_software_action():
    result = classify_prompt("create a website architecture and code structure")
    assert result.intent == INTENT_SOFTWARE_ACTION


def test_brain_route_command_payload():
    payload = brain_route("busca cinco sitios web sobre marketing")
    assert payload["intent"] == INTENT_RESEARCH_ACTION
    assert payload["language"] == "es"
