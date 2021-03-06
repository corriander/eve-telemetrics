import os
import unittest
from unittest import mock

import evetele
from evetele import db


class TestDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure we're reading the local config file
        path = os.path.join(evetele.LOCAL_CONFIG_DIR, 'config.ini')
        evetele.config = evetele.CustomConfigParser(path)
        # Just to be certain this is only reading the local file:
        assert evetele.config.config_paths == path

    def test_conn_details(self):
        """Property contains connection details for the database.

        The connection details are sourced from the config file(s)
        located in the usual app dirs (dependent on OS).
        """
        database = db.Database()
        self.assertEqual(database.conn_details['host'], 'localhost')

    @mock.patch('psycopg2.connect')
    def test_conn(self, stub_connect):
        """Property lazily instantiates a connection object.

        After creating a connection, the session is set to readonly
        and autocommit to avoid issues with hanging transactions (only
        SELECT is used; we don't want to modify the static data).

        Note: the conn property also prompts for a password on
        creating a new connection if it hasn't been provided in the
        config but this isn't tested here.
        """
        database = db.Database()

        self.assertFalse(stub_connect.called)

        value = database.conn

        # Check the DBAPI has been invoked correctly
        expected_parameters = {
            'cursor_factory': database.default_cursor_factory
        }
        expected_parameters.update(database.conn_details)
        stub_connect.assert_called_once_with(**expected_parameters)

        # Check the object return by the connect attempt is used.
        mock_connection = stub_connect.return_value
        mock_connection.set_session.assert_called_once_with(
            autocommit=True,
            readonly=True
        )
        self.assertIs(value, mock_connection)

    @mock.patch('evetele.db.Database.conn',
                new_callable=mock.PropertyMock)
    def test_default_cursor_factory(self, stub_property):
        """Property handles setting connection's cursor factory.

        The setter assigns the new value to the internal attribute on
        the class and the `cursor_factory` attribute of the connection
        stored in the `conn` property.
        """
        database = db.Database()
        database.default_cursor_factory = 'foo'

        self.assertEqual(database.default_cursor_factory, 'foo')
        self.assertEqual(stub_property.return_value.cursor_factory,
                         'foo')

    @mock.patch('evetele.db.Database.conn',
                new_callable=mock.PropertyMock)
    def test_query(self, stub_property):
        """Method wraps psycopg2's DBAPI compatible execute method."""
        database = db.Database()

        # Reference the mock connection and expected execute args
        mock_connection = stub_property.return_value
        args, kwargs = ('sql statement', 'foo'), dict(kw='bar')

        # Invoke
        cursor = database.query(*args, cursor_factory='baz', **kwargs)

        # Check the connection/cursor is used properly.
        mock_connection.cursor.assert_called_once_with(
            cursor_factory='baz'
        )
        self.assertIs(cursor, mock_connection.cursor.return_value)
        cursor.execute.assert_called_once_with(*args, **kwargs)

    @mock.patch('evetele.db.Database.query')
    def test_schema(self, stub_query):
        """Property is a dict of tables and columns."""
        mock_cursor = stub_query.return_value
        mock_cursor.fetchall.return_value = [
            ('table1', 'columnA', 1),
            ('table1', 'columnB', 2),
            ('table2', 'columnC', 1),
            ('table2', 'columnD', 2),
        ]

        database = db.Database()
        self.assertEqual(
            database.schema,
            {'table1': ['columnA', 'columnB'],
             'table2': ['columnC', 'columnD']}
        )

    @mock.patch('evetele.db.Database.schema',
                new_callable=mock.PropertyMock)
    def test_tables(self, stub_property):
        """Property is a list of tables taken from the schema dict."""
        dummy_schema = {
            'table1': ['columnA', 'columnB'],
            'table2': ['columnC', 'columnD'],
        }
        stub_property.return_value = dummy_schema
        database = db.Database()

        self.assertCountEqual(database.tables, dummy_schema.keys())


if __name__ == '__main__':
    unittest.main()
