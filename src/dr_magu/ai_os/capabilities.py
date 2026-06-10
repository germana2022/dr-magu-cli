from __future__ import annotations

from .models import OSCapability


AI_OS_LAYERS = [
    "conversation",
    "routing",
    "llm",
    "mcp",
    "agents",
    "workflows",
    "execution",
    "scheduler",
    "software_factory",
    "self_healing",
    "plugins",
    "permissions",
]


AI_OS_CAPABILITIES = [
    OSCapability("chat", "Chat", "brain.ask", "conversation", "Conversational interaction with Dr Magu."),
    OSCapability("route", "Route", "router.route", "routing", "Route natural-language prompts to commands."),
    OSCapability("llm", "LLM Runtime", "llm.chat", "llm", "Call the configured default LLM provider."),
    OSCapability("mcp", "MCP Servers", "mcp.servers", "mcp", "Inspect configured MCP servers."),
    OSCapability("research", "Research", "research.search", "mcp", "Run research through the research runtime."),
    OSCapability("website", "Website Analysis", "website.analyze", "mcp", "Analyze websites through MCP integration contracts."),
    OSCapability("repository", "Repository Read", "repository.read", "mcp", "Read repository metadata through MCP/GitHub contracts."),
    OSCapability("multiagent", "Multi-Agent Orchestration", "multiagent.run", "agents", "Coordinate multiple agents."),
    OSCapability("factory", "Software Factory", "factory.run", "software_factory", "Run idea-to-delivery software factory pipeline."),
    OSCapability("healing", "Self-Healing", "healing.run", "self_healing", "Run commands with retry, fallback and escalation."),
    OSCapability("scheduler", "Scheduler", "schedule.list", "scheduler", "Manage background schedules."),
    OSCapability("execution", "Execution", "execution.plan.execute", "execution", "Execute planned actions."),
    OSCapability("plugins", "Plugins", "plugin.list", "plugins", "Inspect and manage plugins."),
    OSCapability("permissions", "Permissions", "permissions.show", "permissions", "Inspect effective permissions."),
]
