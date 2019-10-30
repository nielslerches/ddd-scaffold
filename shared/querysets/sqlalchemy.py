from dataclasses import dataclass, field
from functools import reduce
from itertools import islice, tee
from typing import Callable, Any, Iterable, List, Optional

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

import sqlalchemy as sa
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.query import Query


def get_class_by_tablename(tablename, Base):
    for c in Base._decl_class_registry.values():
        if hasattr(c, '__tablename__') and c.__tablename__ == tablename:
            return c


@dataclass(frozen=True)
class SQLAlchemyCompiler:
    def compile(self, node):
        if isinstance(node, A):
            if isinstance(node, GetAttr):
                return lambda model: getattr(
                    self.compile(node.parent)(model),
                    self.compile(node.arguments)(model),
                )

            return lambda model: getattr(model, node.arguments)

        elif isinstance(node, BinaryOperation):
            return lambda model: reduce(
                node.reducer,
                [
                    self.compile(operand)(model)
                    for operand
                    in node.operands
                ],
            )

        elif isinstance(node, Has):
            return lambda model: getattr(
                model,
                node.field,
            ).any(
                self.compile(node.query)(
                    get_class_by_tablename(
                        tuple(sa.inspect(model).relationships[node.field].remote_side)[0].table.name,
                        model.__bases__[0]
                    )
                )
            )

        else:
            return lambda model: node if not isinstance(node, LazyObject) else self.compile(node)(model)


@dataclass(frozen=True)
class SQLAlchemyQuerySet(QuerySet):
    session: Session
    model: Any
    compiler: SQLAlchemyCompiler = field(default_factory=lambda: SQLAlchemyCompiler())
    query: Optional[Query] = field(default=None)

    def all(self):
        return self

    def filter(self, *queries):
        clauses = [
            self.compiler.compile(query)(self.model)
            for query
            in queries
        ]

        return type(self)(
            session=self.session,
            model=self.model,
            compiler=self.compiler,
            query=self.query.filter(*clauses) if self.query is not None else self.session.query(self.model).filter(*clauses),
        )

    def __iter__(self):
        if self.query is None:
            result_set = self.session.query(self.model).all()
        else:
            result_set = self.query.all()
        return iter(result_set)
