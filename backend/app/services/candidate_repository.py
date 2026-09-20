import json
from pathlib import Path

from app.models.candidate import Candidate


class CandidateRepository:
    def __init__(self, dataset_path: Path):
        self.dataset_path = dataset_path
        self._candidates: list[Candidate] | None = None

    def all(self) -> list[Candidate]:
        if self._candidates is None:
            raw_data = json.loads(self.dataset_path.read_text(encoding="utf-8"))
            self._candidates = [Candidate.model_validate(item) for item in raw_data]
        return list(self._candidates)
