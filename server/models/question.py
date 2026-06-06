from dataclasses import dataclass
from typing import Optional


@dataclass
class Question:
    id: int
    term: str
    real_definition: str
    category: str = "通用"
    source: str = "builtin"
    contributor_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "term": self.term,
            "real_definition": self.real_definition,
            "category": self.category,
            "source": self.source,
        }
