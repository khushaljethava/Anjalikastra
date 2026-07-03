import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))

from fixture_site import FixtureSite  # noqa: E402


@pytest.fixture
def fixture_site():
    site = FixtureSite().start()
    yield site
    site.stop()
