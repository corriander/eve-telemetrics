import abc
import collections

from . import static, util, market


class _Location(static.StaticEntity):

    @abc.abstractproperty
    def _market_path(self):
        return

    @property
    def _market(self):
        # Making this available on the class causes circ. dep. issues.
        return market.global_market

    @property
    def market_node(self):
        """The market node (dict) relevant to this instance."""
        root = self._market
        path = self._market_path
        node = root
        for child in path:
            node = node[child]
        return node

    @property
    def orders(self):
        """A dictionary of buy orders for this location."""
        def descend(node):
            for key, value in node.items():
                if isinstance(value, list):
                    for order in value:
                        yield key, order
                else:
                    yield from descend(value)

        orders = collections.defaultdict(list)
        for type_id, order in descend(self.market_node):
            orders[type_id].append(order)
        return dict(orders)


class Region(_Location):

    _id_field = 'regionID'
    _table = 'mapRegions'
    _name_field = 'regionName'
    _cache = {}

    @property
    def _market_path(self):
        return [self.id]

    def update_market(self, type_id=None):
        """Update the market dictionary.

        If `type_id` is not specified, the entire regional market will
        be updated, otherwise only orders for that market type will be
        updated. The update is always region-wide and for either all
        types or a single type because this is the degree of freedom
        offered by the ESI API.
        """
        return self._market.update(self.id, type_id)


class RegionDescendant(object):
    """Mixin for descendents of a region."""

    @util.cached_property
    def region(self):
        return Region(self.region_id)

    def update_market(self, type_id=None):
        """Update the market dictionary.

        If `type_id` is not specified, the entire regional market will
        be updated, otherwise only orders for that market type will be
        updated. The update is always region-wide and for either all
        types or a single type because this is the degree of freedom
        offered by the ESI API.
        """
        return self.region.update_market(type_id)


class System(RegionDescendant, _Location):

    _id_field = 'solarSystemID'
    _table = 'mapSolarSystems'
    _name_field = 'solarSystemName'
    _cache = {}

    @property
    def _market_path(self):
        return [self.region.id, self.id]


class Station(_Location, RegionDescendant):

    _id_field = 'stationID'
    _table = 'staStations'
    _name_field = 'stationName'
    _cache = {}

    @property
    def _market_path(self):
        return [self.region.id, self.system.id, self.id]

    @util.cached_property
    def system(self):
        return System(self.system_id)


Location = Station
