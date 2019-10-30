from dataclasses import dataclass
from typing import Tuple

from shared import get_container
from shared.common_query import A
from shared.common_query.aggregations import Has
from shared.querysets.users import UserQuerySet
from shared.utils import SimpleLazyObject


@dataclass(frozen=True)
class UserService:
    user_queryset: UserQuerySet
    min_points_giftcard_value: Tuple[int, int, str] = (
        1000,
        250,
        'free giftcard'
    )

    def get_users_eligible_for_giftcard(self):
        min_points, giftcard_value, reason = self.min_points_giftcard_value
        return (
            (user, giftcard_value, reason)
            for user
            in self.user_queryset.filter(
                A('points') >= min_points,
            ).exclude(
                Has('giftcards').where(A('reason') == reason),
            )
        )


user_service = SimpleLazyObject(
    func=lambda: get_container().resolve(UserService),
)
