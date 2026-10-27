import pytest
from pydantic import ValidationError

from chordarium_engine.models import ArrangementPlan, PartSpec, Song


def spec(role="piano", **kw):
    return PartSpec(role=role, pattern="block", **kw)


def test_velocity_validation():
    with pytest.raises(ValidationError):
        spec(velocity=(0, 50))
    with pytest.raises(ValidationError):
        spec(velocity=(80, 40))
    assert spec(velocity=(40, 60)).velocity == (40, 60)


def test_density_bounds():
    with pytest.raises(ValidationError):
        spec(density=1.5)


def test_unknown_role_rejected():
    with pytest.raises(ValidationError):
        PartSpec(role="guitar", pattern="x")


def test_plan_unique_roles():
    with pytest.raises(ValidationError):
        ArrangementPlan(section_id="s", style="pop_4_4", parts=[spec(), spec()])


def test_song_roundtrip():
    s = Song(title="T", sections=[])
    assert Song.model_validate(s.model_dump()) == s
