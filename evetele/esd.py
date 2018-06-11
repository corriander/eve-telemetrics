"""EVE Static Data

Database adapter and models for working with the Eve Static Data
Export.
"""
import getpass

import psycopg2
import psycopg2.extras

from . import config


class Database(object):

    _pw_prompt = "Password for [{user}@{host}:{port}/{database}]: "

    _default_cursor_factory = psycopg2.extras.NamedTupleCursor

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

    @property
    def default_cursor_factory(self):
        """Defines the default type of cursor returned by a query."""
        return self._default_cursor_factory
    @default_cursor_factory.setter
    def default_cursor_factory(self, value):
        self._default_cursor_factory = value
        self.db.cursor_factory = value

    def query(self, *args, cursor_factory=None, **kwargs):
        """Execute a SQL query against the ESD database instance.

        Parameters
        ----------

        cursor_factory : psycopg2.extensions.cursor, optional
            Specify a specific or custom cursor factory, e.g.
            `DictCursor` or `NamedTupleCursor`. By default this is
            the value of the `default_cursor_factory` class property.

        All other positional and keyword args are passed directly to
        `psycopg2.extensions.cursor.execute`.

        Returns
        -------

        psycopg2.extensions.cursor
            A newly instantiated cursor for the resultset. Strictly
            the type is a subclass of `cursor` defined by the
            `default_cursor_factory` property.
        """
        cursor = self.db.cursor(cursor_factory=cursor_factory)
        cursor.execute(*args, **kwargs)
        return cursor
