# -*- coding: utf-8 -*-
#
from itertools import chain
from .utils import lazyproperty


class Stack(list):
    def is_empty(self):
        return len(self) == 0

    @property
    def top(self):
        if self.is_empty():
            return None
        return self[-1]

    @property
    def bottom(self):
        if self.is_empty():
            return None
        return self[0]

    def size(self):
        return len(self)

    def push(self, item):
        self.append(item)


class QuerySetChain:
    def __init__(self, querysets):
        self.querysets = querysets

    @lazyproperty
    def querysets_counts(self):
        counts = [s.count() for s in self.querysets]
        return counts

    def count(self):
        return self.total_count

    @lazyproperty
    def total_count(self):
        return sum(self.querysets_counts)

    def __iter__(self):
        self._chain = chain(*self.querysets)
        return self

    def __next__(self):
        return next(self._chain)

    def __getitem__(self, ndx):
        querysets_count_zip = zip(self.querysets, self.querysets_counts)
        length = 0   
        pre_length = 0 
        items = []
        loop = 0

        if isinstance(ndx, slice):
            ndx_start = ndx.start or 0
            ndx_stop = ndx.stop or self.total_count
            ndx_step = ndx.step or 1
        else:
            ndx_start = ndx
            ndx_stop, ndx_step = None, None

        for queryset, count in querysets_count_zip:
            length += count
            loop += 1
            if length > ndx_start >= pre_length:
                start = ndx_start - pre_length
                # print("[loop {}] Start is: {}".format(loop, start))
                if ndx_step is None:
                    return queryset[start]
            elif ndx_start >= length:
                pre_length += count
                continue
            else:
                start = 0

            if ndx_stop is None:
                pre_length += count
                continue

            if ndx_stop < length:
                stop = ndx_stop - pre_length
            else:
                stop = count
            # print("[loop {}] Slice: {} {} {}".format(loop, start, stop, ndx_step))
            items.extend(list(queryset[slice(start, stop, ndx_step)]))
            pre_length += count

            if ndx_stop < length:
                break
        return items
