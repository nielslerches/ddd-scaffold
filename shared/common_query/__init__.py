import operator

from functools import reduce
from itertools import groupby


class LazyObject:
    pass


class Comparable(LazyObject):
    def __eq__(self, other):
        return Eq(self, other)

    def __ne__(self, other):
        return Ne(self, other)

    def __gt__(self, other):
        return Gt(self, other)

    def __ge__(self, other):
        return Ge(self, other)

    def __lt__(self, other):
        return Lt(self, other)

    def __le__(self, other):
        return Le(self, other)

    def __and__(self, other):
        return And(self, other)

    def __or__(self, other):
        return Or(self, other)


class ArithmeticOperable(LazyObject):
    def __add__(self, other):
        return Add(self, other)

    def __radd__(self, other):
        return Add(other, self)

    def __sub__(self, other):
        return Sub(self, other)

    def __rsub__(self, other):
        return Sub(other, self)

    def __mul__(self, other):
        return Mul(self, other)

    def __rmul__(self, other):
        return Mul(other, self)

    def __truediv__(self, other):
        return TrueDiv(self, other)

    def __rtruediv__(self, other):
        return TrueDiv(other, self)

    def __floordiv__(self, other):
        return FloorDiv(self, other)

    def __rfloordiv__(self, other):
        return FloorDiv(other, self)

    def __pow__(self, other):
        return Pow(self, other)

    def __rpow__(self, other):
        return Pow(other, self)

    def __mod__(self, other):
        return Mod(self, other)

    def __rmod__(self, other):
        return Mod(other, self)

    def __neg__(self):
        return Neg(self)


class UnaryOperation(Comparable):
    def __init__(self, operand):
        self.operand = operand

    def __repr__(self):
        return '{}({!r})'.format(self.op, self.operand)


class Accessible(Comparable, ArithmeticOperable):
    def __getattr__(self, name):
        if name in dir(type(self)):
            return super(A, self).__getattr__(name)

        return GetAttr(name, self)

    def __call__(self, *args, **kwargs):
        return Call((args, kwargs), self)

    def __getitem__(self, key):
        return GetItem(key, self)

    def __invert__(self):
        return Not(self)


class BinaryOperation(Accessible):
    __slots__ = ('operands',)

    op = '?'
    reducer = None
    precalc = False

    def __init__(self, *_operands):
        operands = []
        for operand in _operands:
            if type(operand) == type(self):
                operands.extend(operand.operands)
            else:
                operands.append(operand)

        if self.precalc and self.reducer:
            groups = [list(group) for _, group in groupby(operands, lambda obj: hash(type(obj)))]
            operands = [reduce(self.reducer, group) for group in groups]

        self.operands = operands

    def __invert__(self):
        if type(self) == Eq:
            return Ne(*self.operands)
        elif type(self) == Ne:
            return Eq(*self.operands)
        elif type(self) == Gt:
            return Le(*self.operands)
        elif type(self) == Ge:
            return Lt(*self.operands)
        elif type(self) == Lt:
            return Ge(*self.operands)
        elif type(self) == Le:
            return Gt(*self.operands)

        return Not(self)

    def __repr__(self):
        return ' {} '.format(self.op).join(repr(operand) for operand in self.operands)


class BooleanOperation:
    pass


class ArithmeticOperation:
    pass


class Eq(BooleanOperation, BinaryOperation):
    op = '=='
    reducer = operator.eq


class Ne(BooleanOperation, BinaryOperation):
    op = '!='
    reducer = operator.ne


class Gt(BooleanOperation, BinaryOperation):
    op = '>'
    reducer = operator.gt


class Ge(BooleanOperation, BinaryOperation):
    op = '>='
    reducer = operator.ge


class Lt(BooleanOperation, BinaryOperation):
    op = '<'
    reducer = operator.lt


class Le(BooleanOperation, BinaryOperation):
    op = '>='
    reducer = operator.le


class And(BooleanOperation, BinaryOperation):
    op = '&'
    reducer = operator.and_


class Or(BooleanOperation, BinaryOperation):
    op = '|'
    reducer = operator.or_


class Not(BooleanOperation, UnaryOperation):
    op = '~'
    reducer = operator.not_

    def __invert__(self):
        return self.operand


class Add(ArithmeticOperation, BinaryOperation):
    op = '+'
    reducer = operator.add
    precalc = True


class Sub(ArithmeticOperation, BinaryOperation):
    op = '-'
    reducer = operator.sub


class Mul(ArithmeticOperation, BinaryOperation):
    op = '*'
    reducer = operator.mul
    precalc = True


class TrueDiv(ArithmeticOperation, BinaryOperation):
    op = '/'
    reducer = operator.truediv


class FloorDiv(ArithmeticOperation, BinaryOperation):
    op = '//'
    reducer = operator.floordiv


class Pow(ArithmeticOperation, BinaryOperation):
    op = '**'
    reducer = operator.pow


class Mod(ArithmeticOperation, BinaryOperation):
    op = '%'
    reducer = operator.mod


class Neg(ArithmeticOperation, ArithmeticOperable, UnaryOperation):
    op = '-'
    reducer = operator.neg

    def __neg__(self):
        return self.operand


class A(Accessible):
    __slots__ = ('arguments', 'parent')

    def __init__(self, arguments, parent=None):
        self.arguments = arguments
        self.parent = parent

    def __repr__(self):
        return 'A({!r})'.format(self.arguments)


class GetAttr(A):
    def __repr__(self):
        return '{!r}.{}'.format(self.parent, self.arguments)


class Call(A):
    def __repr__(self):
        args, kwargs = self.arguments
        arguments = [repr(arg) for arg in args] + ['{}={!r}'.format(kw, repr(arg)) for kw, arg in kwargs.items()]
        arguments = ', '.join(arguments)
        return '{!r}({})'.format(self.parent, arguments)


class GetItem(A):
    def __repr__(self):
        return '{!r}[{}]'.format(self.parent, self.arguments)


class L(Accessible):
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'L({!r})'.format(self.value)


class Has(ArithmeticOperable, Comparable):
    def __init__(self, field, query=None):
        self.field = field
        self.query = query

    def where(self, query):
        return type(self)(
            field=self.field,
            query=query,
        )

    def __repr__(self):
        s = self.__class__.__name__ + '(' + repr(self.field) + ')'
        if self.query is not None:
            s = s + '.where(' + repr(self.query) + ')'
        return s


class Count(ArithmeticOperable, Comparable):
    def __init__(self, field, query=None):
        self.field = field
        self.query = query

    def where(self, query):
        return type(self)(
            field=self.field,
            query=query,
        )

    def __repr__(self):
        s = self.__class__.__name__ + '(' + repr(self.field) + ')'
        if self.query is not None:
            s = s + '.where(' + repr(self.query) + ')'
        return s
