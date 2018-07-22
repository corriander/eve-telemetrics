"""Adapter for EVE Static Data Export.

Communicates with a database via the `db` module to provide an adapter
for querying a copy of the EVE SDE.
"""
import abc

from . import db, config
from .util import cached_property, classproperty


class EveStaticData(object):

    db = db.Database()

    @cached_property
    def regions(self):
        """Metadata for regions and member solar systems."""
        cursor = self.db.query(
            """
            SELECT regions."regionID" AS region_id
                 , regions."regionName" AS region_name
                 , systems."solarSystemID" AS system_id
                 , systems."solarSystemName" AS system_name
                 , stations."stationID" AS station_id
                 , stations."stationName" AS station_name
              FROM "mapRegions" as regions
              JOIN "mapSolarSystems" as systems
                ON systems."regionID" = regions."regionID"
              LEFT JOIN "staStations" as stations
                ON stations."solarSystemID" =
                      systems."solarSystemID"
            """
        )
        regions = {}
        for record in cursor.fetchall():
            # Get or create the dict for this record's region
            region_dict = regions.setdefault(
                record.region_id,
                {'id': record.region_id,
                 'name': record.region_name,
                 'systems': {}}
            )
            # Get or create the dict for this record's system
            system_dict = region_dict['systems'].setdefault(
                record.system_id,
                {'id': record.system_id,
                 'name': record.system_name,
                 'stations': {}}
            )
            # If this record includes a station, add it to the
            # system's stations dict.
            if record.station_id is not None:
                system_dict['stations'][record.station_id] = {
                    'id': record.station_id,
                    'name': record.station_name
                }
        return regions

    @cached_property
    def market_types(self):
        """Metadata for types that can be sold on the market."""
        cursor = self.db.query(
            """
            SELECT "typeID" as id
                 , "typeName" as name
              FROM "invTypes"
             WHERE "marketGroupID" IS NOT NULL
            """
        )

        return {
            rec.id: {attr: getattr(rec, attr) for attr in rec._fields}
            for rec in cursor.fetchall()
        }

    @cached_property
    def stations(self):
        """Metadata for stations."""
        stations = {}
        for system_id, system_dict in self.systems.items():
            for station_id, station_dict in (
                    system_dict['stations'].items()):
                stations[station_id] = station_dict
        return stations

    @cached_property
    def systems(self):
        """Metadata for solar systems."""
        systems = {}
        for region_id, region_dict in self.regions.items():
            for system_id, system_dict in (
                    region_dict['systems'].items()):
                systems[system_id] = system_dict
        return systems

    @cached_property
    def trade_hubs(self):
        """Metadata for trade hub stations."""
        return [
            self.get_metadata('station', id_)
            for id_ in self._trade_hub_ids()
        ]

    def _trade_hub_ids(self):
        # Fetch trade hub ids from config and make sure they're ints
        return map(int, config['Places']['trade hubs'].split(','))

    def get_metadata(self, entity, identifier):
        """Get supported metadata for the specified object.

        Parameters
        ----------

        entity : str in {'region', 'station', 'system'}
            Entity to look up

        identifier: int or str
            Either the entity's ID or its name
        """
        try:
            data = getattr(self, '{}s'.format(entity))
        except AttributeError:
            raise ValueError("Unknown entity '{}'".format(entity))

        if isinstance(identifier, str):
            for metadata in data.values():
                if metadata['name'] == identifier:
                    return metadata
            else:
                raise ValueError(
                    "Unknown {} '{}'".format(entity, identifier)
                )

        else:
            return data[identifier]


class StaticEntity(metaclass=abc.ABCMeta):
    """Base class for classes modelling entities in static data.

    Aside from implementing the abstract methods/properties, a
    subclass may override the _entity_name class property/attribute if
    the entity name (for calling `EveStaticData.get_metadata`) is not
    derivable from the class name. Default behaviour is to lowercase
    and pluralise the class name.
    """
    # NOTE: The EveStaticData API has become a bit deficient as things
    #       have moved on, see the TODOs in this class for some hints
    #       at future improvement.

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
            entity = cls._entity_name
            for k, v in global_esd.get_metadata(entity, id_).items():
                setattr(inst, k, v)
        return inst

    @abc.abstractproperty
    def _cache(self):
        """Class-specific cache."""
        # TODO: Convert this to a classproperty to reduce boilerplate
        #       or abstract the cache content into a subdict mapped to
        #       class.
        return {}

    @abc.abstractproperty
    def _id_field(self):
        """Name of the database column containing the entity ID.

        This is currently required for performing an ID lookup.
        """
        # TODO: Can this be removed? Currently get_metadata scans the
        #       metadata if it's given a name (str) so this sort of
        #       represents a shortcut but also involves a database
        #       call. This might be better contained within
        #       get_metadata, or better yet implement some kind of
        #       reverse lookup. The dicts could even be keyed with
        #       name if they are all unique which is likely.
        return ''

    @abc.abstractproperty
    def _name_field(self):
        """Name of the database column containing the entity name.

        This is currently required for performing an ID lookup.
        """
        return ''

    @abc.abstractproperty
    def _table(self):
        """Name of the database table for the entity.

        This is currently required for performing an ID lookup.
        """
        return ''

    @classproperty
    def _entity_name(cls):
        """The entity name to pass to EveStaticData.get_metadata()."""
        return cls.__name__.lower()

    @classmethod
    def get_id(cls, name):
        """Given a name, return the ID for an instance of this type.

        This lookup is performed against the local SDE database and
        uses configurable attributes on this class to define the
        query.
        """
        record = global_esd.db.query(
            """
            SELECT "{}"
              FROM "{}"
             WHERE "{}" = %s
            """.format(cls._id_field, cls._table, cls._name_field),
            (name,)
        ).fetchone()
        return getattr(record, cls._id_field)


global_esd = EveStaticData()
