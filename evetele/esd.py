"""EVE Static Data

Database adapter and models for working with the Eve Static Data
Export.
"""

import psycopg2
import psycopg2.extras

from . import config


class Database(object):

    @property
    def conn_details(self):
        return dict(config.items('ESD Source'))
