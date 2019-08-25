from shared.querysets.memory import MemoryQuerySet


class UserQuerySet:
    pass


class UserMemoryQuerySet(UserQuerySet, MemoryQuerySet):
    pass
