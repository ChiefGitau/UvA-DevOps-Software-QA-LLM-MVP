from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from app.domain.models import Finding, Patch

@dataclass
class RepairContext:
    session_id: str
    workspace_dir: Path
    reports_dir: Path
    patches_dir: Path
    token_budget: int
    model: str

class FindingRepairer(ABC):
    @abstractmethod
    def supports(self, finding: Finding) -> bool: ...

    @abstractmethod
    def repair(self, finding: Finding, ctx: RepairContext) -> Patch: ...
