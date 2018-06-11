import collections
import unittest
from unittest import mock

from evetele import static


class TestEveStaticData(unittest.TestCase):

    sample_region_dict = {
        1001: {'id': 1001, 'name': 'Region1', 'systems': {
            3001: {'id': 3001, 'name': 'SystemA'},
            3002: {'id': 3002, 'name': 'SystemB'}}},
        1002: {'id': 1002, 'name': 'Region2', 'systems': {
            3003: {'id': 3003, 'name': 'SystemC'}}},
        1003: {'id': 1003, 'name': 'Region3', 'systems': {
            3004: {'id': 3004, 'name': 'SystemD'}}}
    }

    def setUp(self):
        static.EveStaticData.db = self.mock_dbobject = mock.Mock()
        self.mock_cursor = self.mock_dbobject.query.return_value

    def test_regions(self):
        """Property is a map of region IDs to region data dicts.

        Regions are tree roots in this data model, with
        solar systems child nodes.

        Note that constellations and stations are not modelled at this
        time.
        """
        self.maxDiff = None
        Record = collections.namedtuple(
            'Record',
            'region_id, region_name, system_id, system_name'
        )

        self.mock_cursor.fetchall.return_value = list(
            Record(*args)
            for args in (
                (1001, 'Region1', 3001, 'SystemA'),
                (1001, 'Region1', 3002, 'SystemB'),
                (1002, 'Region2', 3003, 'SystemC'),
                (1003, 'Region3', 3004, 'SystemD')
            )
        )

        esd = static.EveStaticData()

        self.assertEqual(esd.regions, self.sample_region_dict)

    @mock.patch('evetele.static.EveStaticData.regions',
                new_callable=mock.PropertyMock)
    def test_systems(self, stub_property):
        """Property is a map of system IDs to system data dicts."""
        stub_property.return_value = self.sample_region_dict

        esd = static.EveStaticData()

        self.assertEqual(
            esd.systems,
            {
                3001: {'id': 3001, 'name': 'SystemA'},
                3002: {'id': 3002, 'name': 'SystemB'},
                3003: {'id': 3003, 'name': 'SystemC'},
                3004: {'id': 3004, 'name': 'SystemD'}
            }
        )


if __name__ == '__main__':
    unittest.main()
