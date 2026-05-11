from src.orbitlab.combat import resolve_combat


def test_single_enemy_captures_when_surplus_exceeds_garrison():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 18)])
    assert owner == 1
    assert ships == 8


def test_single_enemy_damages_without_capture():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 7)])
    assert owner == 0
    assert ships == 3


def test_friendly_arrival_reinforces():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(0, 5)])
    assert owner == 0
    assert ships == 15


def test_top_two_attackers_duel_before_planet_combat():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 20), (2, 13)])
    assert owner == 0
    assert ships == 3


def test_tied_top_attackers_destroy_each_other():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 20), (2, 20), (3, 5)])
    assert owner == 0
    assert ships == 10


def test_same_owner_arrivals_are_grouped():
    owner, ships = resolve_combat(owner=0, garrison=10, arrivals=[(1, 6), (1, 7)])
    assert owner == 1
    assert ships == 3
