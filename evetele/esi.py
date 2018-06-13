"""Models for working with the EVE API, ESI."""
import functools
import itertools

import esipy

import evetele


USER_AGENT_STRING = '{} {} ({})'.format(
    evetele.HUMAN_APP_NAME,
    evetele.__version__,
    'https://github.com/corriander/eve-telemetrics'
)


class ESIClient(object):

    class BadResponse(Exception):
        def __init__(self, response):
            self.response = response
            msg = "Bad response: {}".format(response.status)
            super().__init__(msg)

    @property
    def _app(self):
        # Lazily evaluated, cached esipy app instance
        try:
            return self.__app
        except AttributeError:
            self.__app = esipy.EsiApp().get_latest_swagger
            return self.__app

    @property
    def _client(self):
        # Lazily evaluated, cached esipy client instance
        try:
            return self.__client
        except AttributeError:
            self.__client = esipy.EsiClient(
                retry_requests=True,
                headers={'User-Agent': USER_AGENT_STRING},
                raw_body_only=False # most of the time we'll parse
            )
            return self.__client

    def _get_op(self, endpoint):
        # De-couples the EsiApp instance from things that want an op,
        # principally makes things easier to test/mock.
        return self._app.op[endpoint]

    def request(self, endpoint, **kwargs):
        """Construct and perform a request.

        Parameters
        ----------

        endpoint : str
            Swagger endpoint description

        Any keyword arguments are used as parameters in the request.

        Returns
        -------

        pyswagger.io.Response
        """
        operation = self._get_op()(**kwargs)
        return self._client.request(operation)

    def multipage_request(self, endpoint, **kwargs):
        """Construct and perform a multipage request.

        Where a resource has more than one page of data, this method
        will iterate through each page (with concurrency) and
        compile the result.

        Parameters
        ----------

        endpoint : str
            Swagger endpoint description

        Any keyword arguments are used as parameters in the request.

        Returns
        -------

        list of (pyswagger.io.Request, pyswagger.io.Response)
            Request-response pairs for every page in the query.
        """
        fetch_page = functools.partial(
            self._get_op(endpoint),
            **kwargs
        )
        response = self._client.head(fetch_page(page=1))

        if response.status == 200:
            npages = response.header['X-Pages'][0]
            operations = [fetch_page(page=i+1) for i in range(npages)]
            return self._client.multi_request(operations)

        else:
            raise self.BadResponse(response)
