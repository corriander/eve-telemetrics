import os
import unittest

import evetele
from evetele import esd


class Database(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure we're reading the local config file
        path = os.path.join(evetele.LOCAL_CONFIG_DIR, 'config.ini')
        evetele.config = evetele.CustomConfigParser(path)
        # Just to be certain this is only reading the local file:
        assert evetele.config.config_paths == path

    def test_conn_details(self):
        """Property contains connection details for the database."""
        db = esd.Database()
        self.assertEqual(db.conn_details['host'], 'localhost')


if __name__ == '__main__':
    unittest.main()
