"""Models for working with the EVE API, ESI."""
import abc
import functools
import itertools

import esipy

import evetele
from evetele.util import cached_property


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

    @cached_property
    def _client(self):
        # Lazily evaluated, cached esipy client instance
        return esipy.EsiClient(
            retry_requests=True,
            headers=self.headers,
            raw_body_only=False # most of the time we'll parse
        )

    @cached_property
    def headers(self):
        return {'User-Agent': USER_AGENT_STRING}

    def _get_op(self, endpoint):
        # De-couples the EsiApp instance from things that want an op,
        # principally makes things easier to test/mock.
        return self._app.op[endpoint]

    def fetch(self, endpoint, **kwargs):
        """Fetch data from the specified endpoint.

        Parameters
        ----------

        endpoint : str
            Swagger endpoint descriptor.

        Any keyword arguments are used as parameters in the request.

        Returns
        -------

        variable
            Data is returned directly from the API and depends on the
            endpoint.
        """
        operation = self._get_op(endpoint)
        if operation_is_multipage(operation):
            # Change type of request params to operation
            req_resp_list = self.multipage_request(endpoint, **kwargs)
            data_generator = (pair[1].data for pair in req_resp_list)
            return list(itertools.chain(*data_generator))

        else:
            resp = self.request(endpoint, **kwargs)
            return resp.data

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
        operation = self._get_op(endpoint)(**kwargs)
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


class ESIClientWrapper(metaclass=abc.ABCMeta):
    """Provides a method for fetching data from an ESI API endpoint.

    Concrete implementations must provide a `_client_class` property
    which dictates the ESIClient class for the wrapped client. Default
    behaviour for init provides a mechanism for providing an existing
    client instance.
    """

    def __init__(self, client=None):
        """Optionally provide an ESI client on initialisation.

        Parameters
        ----------

        client : evetele.esi.ESIClient, optional
            An existing ESI client instance.
        """
        if client is not None:
            if not isinstance(client, self._client_class):
                raise TypeError(
                    "`client` init argument must be an instance of "
                    "{}.".format(self._client_class.__name__)
                )
                self._client = client

    @abc.abstractproperty
    def _client_class(self):
        return ESIClient

    @cached_property
    def _client(self):
        return self._client_class()

    def fetch(self, endpoint, **kwargs):
        """Fetch data from an endpoint.

        Parameters
        ----------

        endpoint : str
            ESI Swagger endpoint identifier.

        Any API endpoint parameters must be provided as keyword
        arguments.

        Notes
        -----

        The client type dictates which ESI endpoints will be
        accessible. For endpoints requiring authorisation, a
        secure ESI client instance must be used (e.g.
        `SecureESIClient`) and this concrete implementation must be
        configured to use that type via `_client_class`.
        """
        return self._client.fetch(endpoint, **kwargs)


def operation_is_multipage(op):
    """Identify whether operation has a page parameter."""
    # This is a bit magic and touches pyswagger internals.
    return 'page' in [getattr(param, '$ref').split('/')[-1]
                      for param in op.parameters]
