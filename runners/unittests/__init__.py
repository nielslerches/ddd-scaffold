import pkgutil
import unittest

from importlib import import_module

from punq import Container

from shared import set_container
from shared.querysets.base import QuerySet
from shared.querysets.memory import MemoryQuerySet
from shared.querysets.users import UserQuerySet, UserMemoryQuerySet
from shared.services import UserService

container = Container()
container.register(QuerySet, instance=MemoryQuerySet)
container.register(UserQuerySet, factory=UserMemoryQuerySet)
container.register(UserService)

set_container(container)


def get_submodules(package):
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        submodule = importer.find_module(modname).load_module(modname)
        yield submodule

        if ispkg:
            yield from get_submodules(
                importer.find_module(
                    submodule.__spec__.name,
                ).load_module(
                    submodule.__spec__.name,
                ),
            )


def get_module_test_cases(module):
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            yield obj


def run():
    test_case_classes = []
    test_module = import_module('runners.unittests.tests')
    for module in get_submodules(test_module):
        for test_case_cls in get_module_test_cases(module):
            test_case_classes.append(test_case_cls)

    for test_case_cls in test_case_classes:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_case_cls)
        unittest.TextTestRunner().run(suite)
