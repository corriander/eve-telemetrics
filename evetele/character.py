from . import esi, trade, util


class Character(esi.ESIClientWrapper):
    """Representation of a character via an authorised ESI session.

    The character is defined by the application details for the
    account, and the refresh token generated from the original
    selection during the authorisation process.

    Currently only one character's details are supported, but a
    character on the same account can be changed by dropping the
    refresh token from the configuration file and re-authenticating
    (this will be triggered on invocation of a method requiring
    authenticated access to the API).
    """

    _client_class = esi.SecureESIClient

    @property
    def name(self):
        """The character's name."""
        try:
            return self._name
        except AttributeError:
            self._get_api_info()
            return self._name

    @property
    def id(self):
        """The character's ID."""
        try:
            return self._id
        except AttributeError:
            self._get_api_info()
            return self._id

    def _get_api_info(self):
        api_info = self._client.get_api_info()
        self._name = api_info['CharacterName']
        self._id = api_info['CharacterID']

    def open_orders(self):
        """Fetch current market orders for this character.

        Returns
        -------

        list of trade.MarketOrderSnapshot
        """
        now = util.get_utc_datetime()
        lst = self.fetch(
            endpoint='characters_character_id_orders',
            character_id=self.id
        )
        orders = [trade.MarketOrderSnapshot(d, t=now) for d in lst]

        return orders
