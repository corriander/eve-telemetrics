class cached_property(object):
    # It's probably more sophisticated to use lru_cache or similar a
    # la https://stackoverflow.com/a/33672499/8992969

    def __init__(self, fget):
        self.fget = fget
        self.__doc__ = fget.__doc__
        self.name = name = fget.__name__
        self.iname = '_{}'.format(name)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        try:
            return getattr(obj, self.iname)
        except AttributeError:
            value = self.fget(obj)
            setattr(obj, self.iname, value)
            return value
