import collections
import unittest
from unittest import mock

import ddt

from evetele import static

from . import mock_property


@ddt.ddt
class TestEveStaticData(unittest.TestCase):

    sample_region_dict = {
        1001: {'id': 1001, 'name': 'Region1', 'systems': {
            3001: {'id': 3001, 'name': 'SystemA', 'stations': {}},
            3002: {'id': 3002, 'name': 'SystemB', 'stations': {}}}},
        1002: {'id': 1002, 'name': 'Region2', 'systems': {
            3003: {'id': 3003, 'name': 'SystemC', 'stations': {}}}},
        1003: {'id': 1003, 'name': 'Region3', 'systems': {
            3004: {'id': 3004, 'name': 'SystemD', 'stations': {
                6001: {'id': 6001, 'name': 'StationA'}}}}},
    }

    sample_system_dict = {
        3001: {'id': 3001, 'name': 'SystemA', 'stations': {}},
        3002: {'id': 3002, 'name': 'SystemB', 'stations': {}},
        3003: {'id': 3003, 'name': 'SystemC', 'stations': {}},
        3004: {'id': 3004, 'name': 'SystemD', 'stations': {
            6001: {'id': 6001, 'name': 'StationA'}}},
    }

    def setUp(self):
        static.EveStaticData.db = self.mock_dbobject = mock.Mock()
        self.mock_cursor = self.mock_dbobject.query.return_value

    def test_market_types(self):
        """Property provides a lookup capability for market items.

        Generally we're dealing with IDs and want human-readable
        information.
        """
        DummyRecord = collections.namedtuple('Record', 'id, name')
        self.mock_cursor.fetchall.return_value = [
            DummyRecord(123, 'A thing'),
            DummyRecord(321, 'Another thing')
        ]

        esd = static.EveStaticData()
        self.assertEqual(
            esd.market_types,
            {123: {'id': 123, 'name': 'A thing'},
             321: {'id': 321, 'name': 'Another thing'}}
        )

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
            ['region_id', 'region_name', 'system_id',
             'system_name', 'station_id', 'station_name']
        )
        self.mock_cursor.fetchall.return_value = list(
            Record(*args)
            for args in (
                (1001, 'Region1', 3001, 'SystemA', None, None),
                (1001, 'Region1', 3002, 'SystemB', None, None),
                (1002, 'Region2', 3003, 'SystemC', None, None),
                (1003, 'Region3', 3004, 'SystemD', 6001, 'StationA')
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
        self.assertEqual(esd.systems, self.sample_system_dict)

    @mock.patch('evetele.static.EveStaticData.systems',
                new_callable=mock.PropertyMock)
    def test_stations(self, stub_property):
        """Property is a map of station IDs to station data dicts."""
        stub_property.return_value = self.sample_system_dict
        esd = static.EveStaticData()
        self.assertEqual(
            esd.stations,
            {6001: {'id': 6001, 'name': 'StationA'}}
        )

    @mock.patch('evetele.static.EveStaticData.stations',
                new_callable=mock.PropertyMock)
    @mock.patch('evetele.static.EveStaticData._trade_hub_ids')
    def test_trade_hubs(self, mock_id_getter, mock_stations):
        """Property is a list of trade hub metadata.

        Trade hubs are set in config and retrieved via _trade_hub_ids.
        """
        mock_id_getter.return_value = 456, 654

        mock_stations.return_value = {
            456: {'id': 456, 'name': 'Mega Trade Hub'},
            654: {'id': 654, 'name': 'Lesser Trade Hub'},
            555: {'id': 555, 'name': 'Port Middle-of-Nowhere'}
        }

        esd = static.EveStaticData()
        self.assertEqual(
            esd.trade_hubs,
            [{'id': 456, 'name': 'Mega Trade Hub'},
             {'id': 654, 'name': 'Lesser Trade Hub'}]
        )

    @ddt.data(
        ('region', 'regions'),
        ('system', 'systems'),
        ('station', 'stations'),
        ('market_type', 'market_types')
    )
    @ddt.unpack
    def test_get_metadata(self, entity_name, prop_name):
        """Get metadata should invoke the right property."""
        with mock_property(static.EveStaticData, prop_name) as stub:
            dummy_data = expected = {'some': 'data'}
            stub.return_value = {-1: dummy_data}
            esd = static.EveStaticData()
            retval = esd.get_metadata(entity_name, -1)
            self.assertIs(retval, expected)


# See test_place for test cases exercising the StaticEntity ABC via
# concrete implementations.


if __name__ == '__main__':
    unittest.main()
