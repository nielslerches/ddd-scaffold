from dataclasses import dataclass, field
from functools import reduce
from itertools import islice, tee
from typing import Callable, Any, Iterable, List

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
)
from shared.common_query.aggregations import (
    Aggregation,
    Count,
    Sum,
    Has,
    Mean,
    Collect,
)
from shared.querysets.base import QuerySet


def nwise(xs, n=2):
    return zip(*(islice(xs, idx, None) for idx, xs in enumerate(tee(xs, n))))


def isiterable(obj):
    try:
        iter(obj)
    except TypeError:
        return False
    return True


@dataclass(frozen=True)
class LambdaCompiler:
    get_value: Callable[[Any, str], Any] = field(default=getattr)

    def compile(self, node):
        if isinstance(node, A):
            if isinstance(node, GetAttr):
                return lambda item: getattr(
                    self.compile(node.parent)(item),
                    self.compile(node.arguments)(item)
                )

            elif isinstance(node, Call):
                args, kwargs = node.arguments
                return lambda item: self.compile(node.parent)(item)(
                    *[(self.compile(arg)(item)) for arg in args],
                    **{
                        kw: (self.compile(arg)(item))
                        for kw, arg
                        in kwargs.items()
                    }
                )

            elif isinstance(node, GetItem):
                return lambda item: self.compile(node.parent)(item)[
                    self.compile(node.arguments)(item)
                ]

            elif isinstance(node, L):
                return lambda item: node.value

            return lambda item: self.get_value(
                item,
                self.compile(node.arguments)(item)
            )

        elif isinstance(node, BinaryOperation):
            if isinstance(node, BooleanOperation):
                return lambda item: all(
                    node.reducer(
                        (self.compile(a)(item)),
                        (self.compile(b)(item))
                    )
                    for a, b
                    in nwise(node.operands)
                )

            return lambda item: reduce(
                node.reducer,
                [
                    (self.compile(operand)(item))
                    for operand
                    in node.operands
                ]
            )

        elif isinstance(node, UnaryOperation):
            return lambda item: node.reducer(self.compile(node.operand)(item))

        elif isinstance(node, Aggregation):
            def compiled_Aggregation(context):
                if isinstance(context, MemoryQuerySet):
                    return node.reducer(context.filter(node.query))
                return node.reducer(
                    MemoryQuerySet(
                        get_objects=lambda: self.get_value(context, node.field),
                        compiler=self,
                    ).filter(node.query)
                )
            return compiled_Aggregation

        else:
            return lambda item: node if not isinstance(node, LazyObject) else self.compile(node)(item)


@dataclass(frozen=True)
class MemoryQuerySet(QuerySet):
    get_objects: Callable[[Any], Iterable] = field(default=lambda: [])
    compiler: LambdaCompiler = field(default_factory=LambdaCompiler)
    pipeline: List[Callable[[Any], Iterable]] = field(default_factory=list)

    class MultipleObjectsReturned(Exception):
        message = 'Multiple objects returned'

    class ObjectDoesNotExist(Exception):
        message = 'Object does not exist'

    def all(self):
        return self

    def filter(self, *queries):
        callbacks = [self.compiler.compile(query) for query in queries if query is not None]

        def _filter(objects):
            return [
                object
                for object
                in objects
                if all(callback(object) for callback in callbacks)
            ]

        return type(self)(
            get_objects=self.get_objects,
            compiler=self.compiler,
            pipeline=self.pipeline + [_filter]
        )

    def exclude(self, *queries):
        callbacks = [self.compiler.compile(query) for query in queries if query is not None]

        def _exclude(objects):
            return [
                object
                for object
                in objects
                if any(not callback(object) for callback in callbacks)
            ]

        return type(self)(
            get_objects=self.get_objects,
            compiler=self.compiler,
            pipeline=self.pipeline + [_exclude],
        )

    def order_by(self, *fields):
        def _order_by(objects):
            objects = objects.copy()
            for field in reversed(fields):
                if isinstance(field, Neg):
                    objects.sort(key=lambda object: self.compiler.compile(field.operand)(object), reverse=True)
                else:
                    objects.sort(key=lambda object: self.compiler.compile(field)(object))
            return objects

        return type(self)(
            get_objects=self.get_objects,
            compiler=self.compiler,
            pipeline=self.pipeline + [_order_by]
        )

    def get(self, *queries):
        objects = list(self.filter(*queries))
        if len(objects) > 1:
            raise self.MultipleObjectsReturned
        elif not objects:
            raise self.ObjectDoesNotExist
        return objects[0]

    def first(self):
        objects = list(self)
        return objects[0] if objects else None

    def last(self):
        objects = list(self)
        return objects[-1] if objects else None

    def aggregate(self, aggregation: Aggregation):
        return aggregation.reducer(self)

    def __iter__(self):
        objects = self.get_objects()
        for pipe in self.pipeline:
            objects = pipe(objects)
        return iter(objects)

    def __repr__(self):
        objects = list(self)
        return '<{} [{}]>'.format(
            self.__class__.__name__,
            ', '.join(
                repr(object)
                for object
                in objects[0:3]
            ) + (', ...' if len(objects) > 3 else '')
        )
