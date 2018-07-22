import abc
import collections

from . import static, util, market


class _Location(metaclass=abc.ABCMeta):

    esd = static.global_esd

    def __new__(cls, ident):
        # convert str or int ident -> int ID, and get or create inst
        id_ = ident if isinstance(ident, int) else cls.get_id(ident)
        try:
            inst = cls._cache[id_]
        except KeyError:
            # Does not exist yet; create, assign metadata and cache.
            # Class names are used to perform the entity lookup on
            # EveStaticData instance.
            inst = cls._cache[id_] = super().__new__(cls)
            entity = cls.__name__.lower()
            for k, v in cls.esd.get_metadata(entity, id_).items():
                setattr(inst, k, v)
        return inst

    @abc.abstractproperty
    def _cache(self):
        return {}

    @abc.abstractproperty
    def _id_field(self):
        return ''

    @abc.abstractproperty
    def _market_path(self):
        return

    @abc.abstractproperty
    def _name_field(self):
        return ''

    @abc.abstractproperty
    def _table(self):
        return ''

    @property
    def _market(self):
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

    @classmethod
    def get_id(cls, name):
        """Given a name, return the ID for an instance of this type.

        This lookup is performed against the local SDE database and
        uses configurable attributes on this class to define the
        query.
        """
        record = cls.esd.db.query(
            """
            SELECT "{}"
              FROM "{}"
             WHERE "{}" = %s
            """.format(cls._id_field, cls._table, cls._name_field),
            (name,)
        ).fetchone()
        return getattr(record, cls._id_field)


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
