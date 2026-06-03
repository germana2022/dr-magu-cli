from __future__ import annotations

from typing import Callable
from pydantic import BaseModel, Field, ConfigDict

from dr_magu.commands.context import CommandContext
from dr_magu.result import ToolResult


CommandHandler = Callable[[dict[str, object], CommandContext], ToolResult]


class CommandDefinition(BaseModel):
    """Metadata and executable handler for a command processor entry."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    category: str
    handler: CommandHandler
    requires_workspace: bool = True
    requires_approval: bool = False
    aliases: list[str] = Field(default_factory=list)
