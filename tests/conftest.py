import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"), "SEED": False, "CURRENCY": "₹"})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "seeded.db"), "SEED": True}).test_client()
