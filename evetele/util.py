import logging

log = logging.getLogger(__name__)


class cached_property(object):
    # It's probably more sophisticated to use lru_cache or similar a
    # la https://stackoverflow.com/a/33672499/8992969

    def __init__(self, fget):
        self.fget = fget
        self.__doc__ = fget.__doc__
        self.name = name = fget.__name__
        self.iname = '_cached_{}'.format(name)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        try:
            return getattr(obj, self.iname)
        except AttributeError:
            value = self.fget(obj)
            setattr(obj, self.iname, value)
            return value


def exception_logger(cls, inst, traceback):
    # Log any unhandled exception.
    log.exception(': '.join([cls.__name__, str(inst)]))
    sys.__excepthook__(cls, inst, traceback)
sys.excepthook = exception_logger
