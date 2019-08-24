import pkgutil
import unittest

from importlib import import_module

from punq import Container

from shared import set_container
from shared.repositories.base import Repository
from shared.repositories.memory import MemoryRepository
from shared.repositories.users import UserRepository, UserMemoryRepository
from shared.services import UserService

container = Container()
container.register(Repository, instance=MemoryRepository)
container.register(UserRepository, factory=UserMemoryRepository)
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
    for module in (test_module, *get_submodules(test_module)):
        for test_case_cls in get_module_test_cases(module):
            test_case_classes.append(test_case_cls)

    while test_case_classes:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            test_case_classes.pop(0),
        )

    unittest.TextTestRunner().run(suite)
