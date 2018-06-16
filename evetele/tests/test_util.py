import unittest
from unittest import mock

from ..util import cached_property


class TestCachedProperty(unittest.TestCase):

    def test_caching(self):

        mock_object = mock.Mock(y=1)

        class A(object):
            species = 'haddock'
            @cached_property
            def x(self):
                mock_object.method(fish=self.species)
                return -1
        a = A()

        self.assertTrue(not hasattr(a, A.x.iname))
        self.assertEqual(a.x, -1)
        mock_object.method.assert_called_once_with(fish='haddock')
        self.assertTrue(hasattr(a, A.x.iname))
        a.species = 'cod'
        a.x
        mock_object.method.assert_called_once_with(fish='haddock')


if __name__ == '__main__':
    unittest.main()
