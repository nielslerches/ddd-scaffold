import unittest

from decimal import Decimal
from functools import partial

from shared.common_query import A
from shared.common_query.aggregations import Has
from shared.querysets.sqlalchemy import SQLAlchemyQuerySet

from sqlalchemy import (
    create_engine,
    Column as NullColumn,
    Integer,
    Numeric,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()
Column = partial(NullColumn, nullable=False)


class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    total = Column(Numeric(precision=2, scale=9))

    items = relationship('OrderItem', back_populates='order')


class OrderItem(Base):
    __tablename__ = 'orderitem'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('order.id'))
    order = relationship('Order', back_populates='items')
    line_total = Column(Numeric(precision=2, scale=9))


class SQLAlchemyQuerySetTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine('sqlite:///:memory:', echo=True)
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        order = Order(total=Decimal('499.00'))
        session.add(order)
        session.add(OrderItem(order=order, line_total=Decimal('499.00')))
        session.add(Order(total=Decimal('129.00')))
        session.commit()

        self.queryset = SQLAlchemyQuerySet(
            session=session,
            model=Order,
        )

    def test_no_filter(self):
        self.assertEqual(len(list(self.queryset.all())), 2)

    def test_with_filter(self):
        self.assertEqual(
            len(
                list(
                    self.queryset.filter(A('total') >= Decimal('499.00'))
                )
            ),
            1
        )

    def test_has_items(self):
        self.assertEqual(
            len(
                list(
                    self.queryset.filter(Has('items')),
                )
            ),
            1
        )

    def test_has_items_where(self):
        self.assertEqual(
            len(
                list(
                    self.queryset.filter(Has('items').where(A('line_total') >= Decimal('1000.00'))),
                )
            ),
            0
        )
