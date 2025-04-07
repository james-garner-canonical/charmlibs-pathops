"""This package should not be installed - it exists solely to reserve the PyPI charmlibs namespace.

For more information, see the PyPI page at https://pypi.org/project/charmlibs
"""

import warnings

__version__ = "0.0.0a0"

warnings.warn("This package should not be installed.", stacklevel=1)
