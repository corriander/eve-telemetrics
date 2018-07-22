import abc
import unittest
from unittest import mock

from .. import place

from . import mock_property


class BaseTestCase(unittest.TestCase, metaclass=abc.ABCMeta):

    @abc.abstractproperty
    def _sut_class(self):
        return place._Location

    @property
    def _example_metadata(self):
        return self.__example_metadata

    @classmethod
    def setUpClass(cls):
        # At no point do we want or need a real EveStaticData instance
        # because it involves I/O.
        cls.global_esd_orig = place.static.global_esd
        place.static.global_esd = mock.Mock()

        def mock_metadata_getter(entity, id_=None):
            return {
                'region': {'id': 1234, 'name': 'ABCD', 'systems': {}},
                'system': {'id': 5678, 'name': 'LMNO', 'stations': {},
                           'region_id': 1234},
                'station': {'id': 9012, 'name': 'XYZ',
                            'region_id': 1234, 'system_id': 5678}
            }[entity]
        place.static.global_esd.get_metadata = mock_metadata_getter
        cls.__example_metadata = mock_metadata_getter(
            cls._sut_class.__name__.lower())

        cls._market = place.market.global_market
        cls._market[1234][5678][9012][34] = [1, 2]
        cls._market[1234][5678][9012][35] = [3, 4]
        cls._market[1234][5678][9013][35] = [5, 6]
        cls._market[1234][5679][9014][36] = [7, 8]

    @classmethod
    def tearDownClass(cls):
        place.static.global_esd = cls.global_esd_orig

    def setUp(self):
        self.sut = self._sut_class(self._example_metadata['id'])


class TestRegion(BaseTestCase):
    """Exercise the Region concrete class and default behaviour.

    `_Location` is an abstract base class extending
    `static.StaticEntity` providing a mandated interface and some
    common behaviour for all subtypes. This test suite doubles up
    exercising the Region concrete [sub]class and the default
    behaviour.

    Because `StaticEntity`'s defined interface was originally
    implemented here, this test case exercises that behaviour.
    """

    _sut_class = place.Region

    def test___new___id(self):
        """A region should be instantiatable by integer ID.

        The region should have the expected properties and be present
        in the cache.

        This is default, base class behaviour.
        """
        place.Region._cache = {}

        self.assertEqual(len(place.Region._cache), 0)
        region = place.Region(1234)

        self.assertEqual(region.name, 'ABCD')
        self.assertIn(region, place.Region._cache.values())

    def test___new___name(self):
        """A region should be instantiatable by name.

        The region should have the expected properties and be present
        in the cache.

        This is default, base class behaviour.
        """
        place.Region._cache = {}

        self.assertEqual(len(place.Region._cache), 0)
        region = place.Region('ABCD')

        self.assertEqual(region.id, 1234)
        self.assertIn(region, place.Region._cache.values())

    def test___new___cache(self):
        """If already instantiated, a region should be re-used.

        This is default, base class behaviour.
        """
        self.assertEqual(len(place.Region._cache), 1)
        cached_region = list(place.Region._cache.values())[0]

        region = place.Region(1234)

        self.assertIs(region, cached_region)

    def test_market_node(self):
        """Retrieves the region node of a market graph.

        This is default, base class behaviour but it relies on
        configuration in the concrete class.
        """
        self.assertIs(self.sut.market_node, self._market[1234])

    def test_orders(self):
        """Property is a single dictionary of orders in the region.

        Orders are organised in lists by region/system/station/type_id
        and this doesn't care what an order is, it'll just collate
        all relevant orders for the region.

        This is default, base class behaviour
        """

        self.assertCountEqual(self.sut.orders[34], [1, 2])
        self.assertCountEqual(self.sut.orders[35], [3, 4, 5, 6])
        self.assertCountEqual(self.sut.orders[36], [7, 8])

    def test_get_id(self):
        """Method returns the ID for a region name.

        This is default, base class behaviour but it relies on
        configuration in the concrete class.
        """
        mock_esd = place.static.global_esd
        stub_record = mock.Mock(regionID=4321)
        stub_cursor = mock_esd.db.query.return_value
        stub_cursor.fetchone.return_value = mock.Mock(regionID=4321)

        self.assertEqual(place.Region.get_id('XYZ'), 4321)
        args, kwargs = mock_esd.db.query.call_args
        self.assertEqual(
            args[0],
            """
            SELECT "regionID"
              FROM "mapRegions"
             WHERE "regionName" = %s
            """
        )
        self.assertEqual(args[1], ('XYZ',))


class TestSystem(BaseTestCase):
    """Exercises the configuration and extended behaviour."""

    _sut_class = place.System

    def test_market_node(self):
        """Retrieves the system node of a market graph.

        This is default, base class behaviour but it relies on
        configuration in the concrete class.
        """
        self.assertIs(self.sut.market_node, self._market[1234][5678])

    def test_orders(self):
        """Property is a single dictionary of orders in the system.

        Orders are organised in lists by region/system/station/type_id
        and this doesn't care what an order is, it'll just collate
        all relevant orders for the system.

        This is default, base class behaviour
        """
        self.assertEqual(self.sut.orders,
                         {34: [1, 2], 35: [3, 4, 5, 6]})

    @mock_property(_sut_class, 'region')
    def test_update_market(self, stub_property):
        """Method updates the station's market.

        This is behaviour contributed by the RegionDescendent mixin
        and implicitly tests the region property.
        """
        self.sut.update_market(34)

        region_obj = stub_property.return_value
        region_obj.update_market.assert_called_with(34)


class TestStation(BaseTestCase):
    """Exercises the configuration and extended behaviour."""

    _sut_class = place.Station

    def test_market_node(self):
        """Retrieves the station node of a market graph.

        This is default, base class behaviour but it relies on
        configuration in the concrete class.
        """
        self.assertIs(self.sut.market_node,
                      self._market[1234][5678][9012])

    def test_orders(self):
        """Property is a single dictionary of orders in the station.

        Orders are organised in lists by region/system/station/type_id
        and this doesn't care what an order is, it'll just collate
        all relevant orders for the station.

        This is default, base class behaviour
        """
        self.assertEqual(self.sut.orders, {34: [1, 2], 35: [3, 4]})

    @mock_property(_sut_class, 'region')
    @mock_property(_sut_class, 'system')
    def test_update_market(self, stub_system, stub_region):
        """Method updates the station's market.

        This is behaviour contributed by the RegionDescendent mixin
        and implicitly tests the region property.
        """
        self.sut.update_market(34)

        region_obj = stub_region.return_value
        region_obj.update_market.assert_called_with(34)


if __name__ == '__main__':
    unittest.main()
