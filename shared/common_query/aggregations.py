from itertools import chain

from shared.common_query import FilterableMixin, ArithmeticOperable, Comparable


class Aggregation:
    pass


class Count(FilterableMixin, ArithmeticOperable, Comparable, Aggregation):
    def reducer(self, queryset):
        return len(list(queryset))


class Sum(FilterableMixin, ArithmeticOperable, Comparable, Aggregation):
    def reducer(self, queryset):
        return sum(queryset.compiler.get_value(object, self.field) for object in queryset)


class Has(FilterableMixin, ArithmeticOperable, Comparable, Aggregation):
    def reducer(self, queryset):
        return any(list(queryset))


class Mean(FilterableMixin, ArithmeticOperable, Comparable, Aggregation):
    def reducer(self, queryset):
        result = Sum(self.field).where(self.query).reducer(queryset)
        result /= Count(self.field).where(self.query).reducer(queryset)
        return result


class Collect(FilterableMixin, ArithmeticOperable, Comparable, Aggregation):
    def reducer(self, queryset):
        result = []

        for object in queryset:
            result.append(queryset.compiler.get_value(object, self.field))

        return result
