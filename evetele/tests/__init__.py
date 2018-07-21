import functools
import os
from unittest import mock


DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Convenience shortcut for mocking properties.
mock_property = functools.partial(
    mock.patch.object,
    new_callable=mock.PropertyMock
)
