"""Fixtures comunes para tests de Componentes-AgentCore."""
import pathlib
import sys

# Hacer importable src/
SRC_ROOT = pathlib.Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_ROOT))

import pytest


@pytest.fixture
def fixtures_dir():
    return pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def composition_map_path(fixtures_dir):
    return fixtures_dir / "composition_map.yml"


@pytest.fixture
def allowed_models_path(fixtures_dir):
    return fixtures_dir / "allowed_models.yml"
