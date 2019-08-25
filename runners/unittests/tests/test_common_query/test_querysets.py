import unittest

from dataclasses import dataclass
from typing import List

from shared.common_query import Count, A
from shared.querysets.memory import MemoryQuerySet


@dataclass
class Item:
    sku: str
    quantity: int


@dataclass
class Cart:
    id: int
    items: List[Item]


class MemoryQuerySetTestCase(unittest.TestCase):
    def test_count(self):
        queryset = MemoryQuerySet(
            get_objects=lambda: [
                Cart(
                    id=1,
                    items=[Item(sku='DX7814-220', quantity=2)],
                ),
                Cart(
                    id=2,
                    items=[Item(sku='DX7814-440', quantity=1)],
                ),
                Cart(
                    id=2,
                    items=[],
                ),
            ]
        )
        self.assertEqual(len(list(queryset.filter(Count('items') == 0))), 1)
        self.assertEqual(len(list(queryset.filter(Count('items').where(A('quantity') > 0)))), 2)
