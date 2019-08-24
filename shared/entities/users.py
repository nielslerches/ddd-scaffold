from dataclasses import dataclass, field
from typing import List

from shared.entities.base import Entity


@dataclass(frozen=True)
class Giftcard:
    value: int
    reason: str

    def subtract(self, value):
        if value > self.value:
            raise ValueError('{} > {}'.format(value, self.value))
        return type(self)(value=self.value - value)


@dataclass
class User(Entity):
    name: str
    points: int = 0
    giftcards: List[Giftcard] = field(default_factory=list)
