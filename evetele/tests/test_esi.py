import abc
import json
import os
import unittest
from unittest import mock

import pyswagger

from .. import esi

from . import DATA_DIR


class TestESIClient(unittest.TestCase):

    def setUp(self):
        self.sut = client = esi.ESIClient()

        # Mock out the esipy resources.
        self.mock_operation = mock.Mock()
        client._get_op = mock.Mock(return_value=self.mock_operation)
        self.mock_client = mock.Mock()
        setattr(client, type(client)._client.iname, self.mock_client)

    def _generate_mock_response(self, data=None, status=200):
        return mock.Mock(spec=pyswagger.io.Response,
                         status=status,
                         data=(data or [{}]))

    @mock.patch.object(esi, 'operation_is_multipage')
    @mock.patch.object(esi.ESIClient, 'multipage_request')
    def test_fetch__strategy__multipage(self, mock_method, mock_test):
        """Multipage request is used if the endpoint is multipage.

        The fetch method is a wrapper implementing a strategy pattern
        to choose the right request method based on whether the ESI
        endpoint response data is paged or not.

        The fetch method will always return a list by virtue of the
        fact that the data is paged (lists are concatenated in the
        response data processing).
        """
        # Force the multipage strategy
        mock_test.return_value = True

        # multipage_request returns a list of (request, response)
        # tuples. We assume they're all status 200 here and don't care
        # about the data content (we use a default provided by the
        # helper).
        mock_request = mock.Mock()
        mock_response = self._generate_mock_response(status=200)
        mock_method.return_value = [(mock_request, mock_response)]

        args, kwargs = ('an_endpoint',), dict(param=1)
        retval = self.sut.fetch(*args, **kwargs)

        # We expect the parameters to be passed straight through to
        # the wrapped esipy client's method and for the first element
        # to be the same as the first element of the first (here only)
        # response data.
        mock_method.assert_called_with(*args, **kwargs)
        self.assertIs(retval[0], mock_response.data[0])

    @mock.patch.object(esi, 'operation_is_multipage')
    @mock.patch.object(esi.ESIClient, 'request')
    def test_fetch__strategy__simple(self, mock_method, mock_test):
        """Normal request is used if the endpoints is not multipage.

        A normal request may return a list or, if appropriate to the
        endpoint, a dict.
        """
        # Force the single page request strategy
        mock_test.return_value = False

        # request returns a response object. We assume it's 200 here
        # and don't care about the data content (we use a default
        # provided by the helper).
        mock_response = self._generate_mock_response(status=200)
        mock_method.return_value = mock_response

        args, kwargs = ('an_endpoint',), dict(param=1)
        retval = self.sut.fetch(*args, **kwargs)

        mock_method.assert_called_with(*args, **kwargs)
        self.assertIs(retval, mock_response.data)

    def test_request(self):
        """Properly wraps the esipy client request method."""
        response = self.mock_client.request.return_value

        retval = self.sut.request('an_endpoint', param=1)

        self.sut._get_op.assert_called_with('an_endpoint')
        self.mock_client.request.called_once_with(self.mock_operation)
        self.assertIs(retval, response)

    def test_multipage_request(self):
        """Properly wraps the esipy client multi_request method.

        Additionally, a HEAD request is performed to get the number of
        pages available (this could be one!).
        """
        # A multipage request starts with a header to get the number
        # of pages then a list of request/response pairs.
        header_response = self.mock_client.head.return_value
        header_response.status = 200
        header_response.header = {'X-Pages': [1]}
        response = self.mock_client.multi_request.return_value

        retval = self.sut.multipage_request('an_endpoint', param=1)

        self.assertIs(retval, response)


class ESIClientWrapperTestCase(unittest.TestCase,
                               metaclass=abc.ABCMeta):
    """Handles boilerplate for testing ESI client wrapper classes.

    Provides a mock client and mocks the fetch method for convenience.
    Concrete test case classes must specify the client wrapper class
    under test. A pre-instantiated example of the wrapper class is
    also provided.

    Where the wrapped client type is SecureESIClient, dummy api_info
    is provided
    """

    @abc.abstractproperty
    def _sut_class(self):
        # Class of system under test
        return object

    @property
    def sample_api_info(self):
        try:
            return self._sample_api_info
        except AttributeError:
            raise NotImplementedError("Only implemented where {} is "
                                      "being wrapped."
                                      .format(esi.SecureESIClient))

    def setUp(self):
        cls = self._sut_class
        self.mock_client = mock.Mock(spec=cls._client_class)
        self.sut = cls(client=self.mock_client)
        self.sut.fetch = mock.Mock()

        # Add an api_info dict as per esipy examples.
        if issubclass(cls._client_class, esi.SecureESIClient):
            with open(os.path.join(DATA_DIR, 'api_info.json')) as f:
                self._sample_api_info = api_info = json.load(f)
            self.mock_client.get_api_info.return_value = api_info


class TestESIClientWrapper(ESIClientWrapperTestCase):
    """This test suite exercises a simple concrete implementation."""
    # It also demonstrates the base test case.

    @property
    def _sut_class(self):
        try:
            return self.__sut_class
        except AttributeError:
            class ConcreteClass(esi.ESIClientWrapper):
                _client_class = esi.ESIClient
                # We actually need to check an unmocked fetched here
                # so we retain it.
                fetch__real = esi.ESIClientWrapper.fetch
            self.concrete_class = self.__sut_class = ConcreteClass
            return self._sut_class

    def test_fetch(self):
        """Wraps the client fetch method properly."""
        args, kwargs = ('an_endpoint',), dict(param=1)
        # Base test case overrides fetch, so we use our special copy.
        retval = self.sut.fetch__real(*args, **kwargs)
        self.mock_client.fetch.assert_called_with(*args, **kwargs)
        self.assertIs(retval, self.mock_client.fetch.return_value)

    def test__provided___init___behaviour__correct_client(self):
        """Wrapper provides default init behaviour to accept a client.

        As long as the client is the same class as defined in
        _client_class, it'll be used (saving the need to instantiate
        multiple client objects).
        """
        mock_client = mock.Mock(spec=esi.ESIClient)
        try:
            inst = self.concrete_class(client=mock_client)
        except:
            raise AssertionError(
                "Failed to instantiate a concrete ESIClientWrapper "
                "with an appropriate client."
            )
        else:
            self.assertIs(inst._client, mock_client)

    def test__provided___init___behaviour__incorrect_client(self):
        """Default init behaviour won't accept inconsistent client.

        If the client provided on init is not an instance of the type
        assigned to _client_class an exception will be raised.
        """
        self.assertRaises(
            TypeError,
            self.concrete_class,
            client=mock.Mock()
        )


class TestFunctions(unittest.TestCase):

    def test_operation_is_multipage__true(self):
        """Checks the operation for a 'page' parameter.

        This assumes a parameter object that has a proper name
        attribute which isn't always the case.
        """
        mock_parameter = mock.Mock()
        mock_parameter.name = 'page' # Gotcha; name on init fails.
        mock_operation = mock.Mock(parameters=[mock_parameter])
        self.assertTrue(esi.operation_is_multipage(mock_operation))

    def test_operation_is_multipage__false(self):
        """Checks the operation for a 'page' parameter.

        This assumes a parameter object that has a proper name
        attribute which isn't always the case.
        """
        mock_parameter = mock.Mock()
        mock_parameter.name = 'region_id'
        mock_operation = mock.Mock(parameters=[mock_parameter])
        self.assertFalse(esi.operation_is_multipage(mock_operation))

    def test_operation_is_multipage__no_name__true(self):
        """Checks the operation for a 'page' parameter.

        Not all parameter objects seem to end up with proper keys, in
        which case this method needs to revert to deriving the
        parameter name from the URI.

        This is unfortunately a bit black magic because it messes
        around with pyswagger operation internals. To check that the
        library still works as we expect it to here we'd probably need
        an integration test to grab an actual operation object and see
        if this all still works, but that involves HTTP I/O and slow
        initialisation.
        """
        mock_parameter = mock.Mock()
        mock_parameter.name = None
        setattr(mock_parameter,
                '$ref',
                'https://blah.com#/parameters/page')
        mock_operation = mock.Mock(parameters=[mock_parameter])
        self.assertTrue(esi.operation_is_multipage(mock_operation))

    def test_operation_is_multipage__no_name__false(self):
        """Checks the operation for a 'page' parameter.

        See comments on test_operation_is_multipage__no_name__true()
        about inconsistent parameter objects and integration.
        """
        mock_parameter = mock.Mock()
        mock_parameter.name = None
        setattr(mock_parameter,
                '$ref',
                'https://blah.com#/parameters/region_id')
        mock_operation = mock.Mock(parameters=[mock_parameter])
        self.assertFalse(esi.operation_is_multipage(mock_operation))


if __name__ == '__main__':
    unittest.main()
