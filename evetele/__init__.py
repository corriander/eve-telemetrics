import configparser
import os

import appdirs


APP_NAME = 'evetele'
SITE_CONFIG_DIR = appdirs.site_config_dir(appname=APP_NAME)
LOCAL_CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..',
                                'config')
USER_CONFIG_DIR = appdirs.user_config_dir(appname=APP_NAME)


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


config = CustomConfigParser([
    os.path.join(path, 'config.ini')
    for path in [LOCAL_CONFIG_DIR, SITE_CONFIG_DIR, USER_CONFIG_DIR]
])
