import pytest
from fastapi import FastAPI
from sqlmodel import Session

from tests.builders import World, build_world
from tests.integration.helpers import Actors, actors_for


@pytest.fixture
def world(session: Session) -> World:
    return build_world(session)


@pytest.fixture
def team_a(app: FastAPI, world: World) -> Actors:
    return actors_for(app, world.a)


@pytest.fixture
def team_b(app: FastAPI, world: World) -> Actors:
    return actors_for(app, world.b)
