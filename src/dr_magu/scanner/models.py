from __future__ import annotations

from pydantic import BaseModel, Field


class DetectedFile(BaseModel):
    """Important repository file detected by the scanner."""

    path: str
    reason: str


class RepositoryScan(BaseModel):
    """Deterministic repository scan result."""

    workspace_path: str
    project_name: str
    project_type: str
    primary_language: str | None = None
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    test_frameworks: list[str] = Field(default_factory=list)
    important_files: list[DetectedFile] = Field(default_factory=list)
    source_roots: list[str] = Field(default_factory=list)
    test_roots: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    file_count: int = 0
    directory_count: int = 0
    ignored_directories: list[str] = Field(default_factory=list)
