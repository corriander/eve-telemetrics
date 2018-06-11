"""Adapter for EVE Static Data Export.

Communicates with a database via the `db` module to provide an adapter
for querying a copy of the EVE SDE.
"""
from . import db


class EveStaticData(object):

    db = db.Database()

    @property
    def regions(self):
        """Metadata for regions and member solar systems."""
        try:
            return self._regions

        except AttributeError:
            cursor = self.db.query(
                """
                SELECT regions."regionID" AS region_id
                     , "regionName" AS region_name
                     , "solarSystemID" AS system_id
                     , "solarSystemName" AS system_name
                  FROM "mapRegions" as regions
                  JOIN "mapSolarSystems" as systems
                    ON systems."regionID" = regions."regionID"
                """
            )
            self._regions = regions = {}
            for record in cursor.fetchall():
                region_dict = regions.setdefault(
                    record.region_id,
                    {'id': record.region_id,
                     'name': record.region_name}
                )
                system_dict = region_dict.setdefault('systems', {})
                system_dict[record.system_id] = {
                    'id': record.system_id,
                    'name': record.system_name
                }
            return regions
