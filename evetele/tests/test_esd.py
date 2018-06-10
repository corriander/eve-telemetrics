import os
import unittest
from unittest import mock

import evetele
from evetele import esd


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
        database = esd.Database()
        self.assertEqual(database.conn_details['host'], 'localhost')

    @mock.patch('psycopg2.connect')
    def test_db(self, stub_connect):
        """Property lazily instantiates a connection object.

        After creating a connection, the session is set to readonly
        and autocommit to avoid issues with hanging transactions (only
        SELECT is used; we don't want to modify the static data).

        Note: the db property also prompts for a password on creating
        a new connection if it hasn't been provided in the config but
        this isn't tested here.
        """
        database = esd.Database()

        self.assertFalse(stub_connect.called)

        value = database.db

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


if __name__ == '__main__':
    unittest.main()
