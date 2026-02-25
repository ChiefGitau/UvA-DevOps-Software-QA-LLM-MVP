from dataclasses import dataclass
from .base import FindingRepairer

@dataclass
class RepairRegistry:
    repairers: list[FindingRepairer]

    def pick(self, finding):
        for r in self.repairers:
            if r.supports(finding):
                return r
        return None
