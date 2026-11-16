import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


@pytest.fixture(scope="session", autouse=True)
def canonical_dataset(django_db_setup, django_db_blocker):
    from practice.dataset import import_canonical_dataset

    with django_db_blocker.unblock():
        import_canonical_dataset()
