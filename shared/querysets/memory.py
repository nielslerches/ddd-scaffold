from dataclasses import dataclass, field
from functools import reduce
from itertools import islice, tee
from typing import Callable, Any, Iterable, List

import inspect

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
    Count,
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
            def compiled_Has(item):
                queryset = MemoryQuerySet(get_objects=lambda: self.get_value(item, node.field), compiler=self)
                queryset = queryset if node.query is None else queryset.filter(node.query)
                return len(list(queryset)) > 0
            return compiled_Has

        elif isinstance(node, Count):
            def compiled_Count(item):
                queryset = MemoryQuerySet(get_objects=lambda: self.get_value(item, node.field), compiler=self)
                queryset = queryset if node.query is None else queryset.filter(node.query)
                return len(list(queryset))
            return compiled_Count

        else:
            return node


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
        callbacks = [self.compiler.compile(query) for query in queries]

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
        callbacks = [self.compiler.compile(query) for query in queries]

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
