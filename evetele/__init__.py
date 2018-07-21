import configparser
import logging
import os

import appdirs

from . import util # Initialise exception logger.


__version__ = '0.x.0'


APP_NAME = 'evetele'
HUMAN_APP_NAME = 'EVE Telemetrics'
SITE_CONFIG_DIR = appdirs.site_config_dir(appname=APP_NAME)
LOCAL_CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..',
                                'config')

USER_CONFIG_DIR = appdirs.user_config_dir(appname=APP_NAME)
USER_DATA_DIR = appdirs.user_data_dir(appname=APP_NAME)

# Ensure all of these exist.
for _dir in USER_CONFIG_DIR, USER_DATA_DIR:
    if not os.path.exists(_dir):
        os.makedirs(_dir)


class CustomConfigParser(configparser.ConfigParser):
    """ConfigParser with automatic read-on-init."""

    def __init__(self, paths):
        """Initialise the parser with one or more config file paths.

        Parameters
        ----------

        paths : str or list of str
        """
        super().__init__()
        self.config_paths = paths
        self.read(paths)

    def refresh(self):
        """Refresh the configuration from disk."""
        self.read(self.config_paths)


config = CustomConfigParser([
    os.path.join(path, 'config.ini')
    for path in [LOCAL_CONFIG_DIR, SITE_CONFIG_DIR, USER_CONFIG_DIR]
])


class LoggingObject(object):

    @property
    def _log(self):
        cls = self.__class__
        try:
            log = cls._shared_logger
        except AttributeError:
            logger_name = self._fq_class_name
            log = cls._shared_logger = logging.getLogger(logger_name)
        finally:
            return log

    @property
    def _fq_class_name(self):
        return '.'.join([self.__class__.__module__,
                         self.__class__.__qualname__])


# Configure root logger
log = logging.getLogger()
logging.basicConfig(
    level=os.environ.get('EVETELE_LOGLEVEL', 'INFO'),
    format=('[%(levelname).1s | %(asctime)s | %(name)30s] '
            '%(message)s'),
    filename=os.path.join(USER_DATA_DIR, 'main.log'),
    filemode='w'
)

console = logging.StreamHandler()
console.setLevel(logging.WARNING)
log.addHandler(console)
