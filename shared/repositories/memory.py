from functools import reduce
from itertools import islice, tee

from shared.common_query import (
    A,
    BinaryOperation,
    BooleanOperation,
    Call,
    GetAttr,
    GetItem,
    L,
    LazyObject,
    Neg,
    UnaryOperation,
    Has,
)


def nwise(xs, n=2):
    return zip(*(islice(xs, idx, None) for idx, xs in enumerate(tee(xs, n))))


def isiterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    return True


class LambdaCompiler:
    __slots__ = ('repository', 'get_value')

    def __init__(self, repository, get_value=None):
        self.repository = repository
        self.get_value = get_value or getattr

    def compile(self, node):
        if isinstance(node, A):
            if isinstance(node, GetAttr):
                return lambda item: getattr(
                    self.compile(node.parent)(item),
                    node.arguments if not isinstance(node.arguments, LazyObject) else self.compile(node.arguments)(item)
                )

            elif isinstance(node, Call):
                args, kwargs = node.arguments
                return lambda item: self.compile(node.parent)(item)(
                    *[(arg if not isinstance(arg, LazyObject) else self.compile(arg)(item)) for arg in args],
                    **{
                        kw: (arg if not isinstance(arg, LazyObject) else self.compile(arg)(item))
                        for kw, arg
                        in kwargs.items()
                    }
                )

            elif isinstance(node, GetItem):
                return lambda item: self.compile(node.parent)(item)[
                    node.arguments if not isinstance(node.arguments, LazyObject) else self.compile(node.arguments)(item)
                ]

            elif isinstance(node, L):
                return lambda item: node.value(item) if not isinstance(node.value, LazyObject) and callable(node.value) else node.value

            return lambda item: self.get_value(
                item,
                node.arguments if not isinstance(node.arguments, LazyObject) else self.compile(node.arguments)(item)
            )

        elif isinstance(node, BinaryOperation):
            if isinstance(node, BooleanOperation):
                return lambda item: all(
                    node.reducer(
                        (self.compile(a)(item) if isinstance(a, LazyObject) else a),
                        (self.compile(b)(item) if isinstance(b, LazyObject) else b)
                    )
                    for a, b
                    in nwise(node.operands)
                )

            return lambda item: reduce(
                node.reducer,
                [
                    (self.compile(operand)(item) if isinstance(operand, LazyObject) else operand)
                    for operand
                    in node.operands
                ]
            )

        elif isinstance(node, UnaryOperation):
            return lambda item: node.reducer(self.compile(node.operand)(item)) if isinstance(node.operand, LazyObject) else node.reducer(node.operand)

        elif isinstance(node, Has):
            return lambda item: len(list(type(self.repository)(_get_entities=lambda: self.get_value(item, node.field), _compiler=self).filter(node.query if node.query is not None else (lambda item: True)))) > 0

        else:
            return node


class MemoryRepository:
    __slots__ = ('_get_entities', '_compiler', '_pipeline')

    class MultipleObjectsReturned(Exception):
        message = 'Multiple objects returned'

    class ObjectDoesNotExist(Exception):
        message = 'Object does not exist'

    def __init__(self, _get_entities=None, _compiler=None, _pipeline=None):
        self._get_entities = _get_entities or (lambda: [])
        self._compiler = _compiler or LambdaCompiler(repository=self)
        self._pipeline = _pipeline or []

    def all(self):
        return self

    def filter(self, query):
        callback = self._compiler.compile(query)
        def _filter(entities):
            return [
                entity
                for entity
                in entities
                if callback(entity)
            ]
        return type(self)(
            _get_entities=self._get_entities,
            _compiler=self._compiler,
            _pipeline=self._pipeline + [_filter]
        )

    def exclude(self, query):
        callback = self._compiler.compile(query)
        def _filter(entities):
            return [
                entity
                for entity
                in entities
                if not callback(entity)
            ]
        return type(self)(
            _get_entities=self._get_entities,
            _compiler=self._compiler,
            _pipeline=self._pipeline + [_filter],
        )

    def order_by(self, *fields):
        def _order_by(entities):
            entities = entities.copy()
            for field in reversed(fields):
                if isinstance(field, Neg):
                    entities.sort(key=lambda entity: self._compiler.compile(field.operand)(entity), reverse=True)
                else:
                    entities.sort(key=lambda entity: self._compiler.compile(field)(entity))
            return entities
        return type(self)(
            _get_entities=self._get_entities,
            _compiler=self._compiler,
            _pipeline=self._pipeline + [_order_by]
        )

    def get(self, query):
        entities = list(self.filter(query))
        if len(entities) > 1:
            raise self.MultipleObjectsReturned
        elif not entities:
            raise self.ObjectDoesNotExist
        return entities[0]

    def first(self):
        entities = list(self)
        return entities[0] if entities else None

    def last(self):
        entities = list(self)
        return entities[-1] if entities else None

    def __iter__(self):
        entities = self._get_entities()
        for pipe in self._pipeline:
            entities = pipe(entities)
        return iter(entities)

    def __repr__(self):
        entities = list(self)
        return '<{} [{}]>'.format(
            self.__class__.__name__,
            ', '.join(
                repr(entity)
                for entity
                in entities[0:3]
            ) + (', ...' if len(entities) > 3 else '')
        )
