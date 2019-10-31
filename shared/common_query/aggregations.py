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


class Median(FilterableMixin, ArithmeticOperable, Comparable, Aggregation):
    def reducer(self, queryset):
        values = list(sorted(queryset.compiler.get_value(object, self.field) for object in queryset))
        length = len(values)

        if length == 0:
            return None

        if length % 2 == 0:
            right = length // 2
            left = right - 1
            right = values[right]
            left = values[left]
            return sum([right, left]) / 2

        return values[length // 2]


class Collect(FilterableMixin, ArithmeticOperable, Comparable, Aggregation):
    def reducer(self, queryset):
        result = []

        for object in queryset:
            result.append(queryset.compiler.get_value(object, self.field))

        return result
