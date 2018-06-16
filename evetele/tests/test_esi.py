import unittest
from unittest import mock

from evetele import esi


class TestESIClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sut = client = esi.ESIClient()

        # Mock out the esipy resources.
        cls.mock_operation = mock.Mock()
        client._get_op = mock.Mock(return_value=cls.mock_operation)
        cls.mock_client = mock.Mock()
        setattr(client, type(client)._client.iname, cls.mock_client)

    def test_request(self):
        response = self.mock_client.request.return_value

        retval = self.sut.request('an_endpoint', param=1)

        self.mock_client.request.called_once_with(self.mock_operation)
        self.assertIs(retval, response)

    def test_multipage_request(self):
        # A multipage request starts with a header to get the number
        # of pages then a list of request/response pairs.
        header_response = self.mock_client.head.return_value
        header_response.status = 200
        header_response.header = {'X-Pages': (1,)}
        response = self.mock_client.multi_request.return_value

        retval = self.sut.multipage_request('an_endpoint', param=1)

        self.assertIs(retval, response)


if __name__ == '__main__':
    unittest.main()
