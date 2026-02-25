from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.models import Finding

@dataclass
class RawToolResult:
    tool: str
    exit_code: int
    stdout: str
    stderr: str
    artifact: str | None = None

@dataclass
class NormalizerContext:
    session_id: str
    workspace_dir: Path
    reports_dir: Path

class FindingNormalizer(ABC):
    @abstractmethod
    def tool_name(self) -> str: ...

    @abstractmethod
    def normalize(self, raw: RawToolResult, ctx: NormalizerContext) -> list[Finding]: ...
