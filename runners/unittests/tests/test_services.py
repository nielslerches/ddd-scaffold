import unittest

from uuid import uuid4

from shared.entities.users import User, Giftcard
from shared.services import UserService
from shared.repositories.users import UserMemoryRepository


class UserServiceTestCase(unittest.TestCase):
    def test_get_users_eligible_for_giftcard(self):
        user_repository = UserMemoryRepository(
            _get_entities=lambda: (
                User(id=uuid4(), name='Jane Doe', points=1200, giftcards=[Giftcard(value=250, reason='welcome giftcard')]),  # Should be excluded  # noqa: E501
                User(id=uuid4(), name='John Doe', points=600),  # Should be excluded  # noqa: E501
                User(id=uuid4(), name='Jane Doe', points=1000),  # Should be included  # noqa: E501
                User(id=uuid4(), name='Jane Doe', points=999),  # should be excluded  # noqa: E501
            )
        )
        user_service = UserService(
            user_repository=user_repository,
            min_points_giftcard_value=(1000, 350, 'welcome giftcard'),
        )
        users_eligible_for_giftcard = list(user_service.get_users_eligible_for_giftcard())  # noqa: E501
        self.assertEqual(len(users_eligible_for_giftcard), 1)
        self.assertEqual(users_eligible_for_giftcard[0][0].points, 1000)
