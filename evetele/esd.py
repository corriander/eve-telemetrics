"""EVE Static Data

Database adapter and models for working with the Eve Static Data
Export.
"""

import psycopg2
import psycopg2.extras

from . import config


class Database(object):

    _pw_prompt = "Password for [{user}@{host}:{port}/{database}]: "

    default_cursor_factory = psycopg2.extras.NamedTupleCursor

    @property
    def conn_details(self):
        return dict(config.items('ESD Source'))

    @property
    def db(self):
        try:
            return self._db
        except AttributeError:
            if 'password' not in self.conn_details:
                password = getpass.getpass(
                    self._pw_prompt.format(**self.conn_details)
                )
            self._db = connection = psycopg2.connect(
                cursor_factory=self.default_cursor_factory,
                **self.conn_details
            )
            connection.set_session(autocommit=True, readonly=True)
            return connection
