from typing import List
from models.game_state import GameState
from models.player_action import PlayerAction
from models.base import Base
from models.position import Position
import math


def calculate_distance(pos1: Position, pos2: Position) -> int:
    """Berechnet die euklidische Distanz zwischen zwei Positionen."""
    return math.floor(math.sqrt(
        (pos1.x - pos2.x)**2 +
        (pos1.y - pos2.y)**2 +
        (pos1.z - pos2.z)**2
    ))


def find_targets(game_state: GameState, player_id: int, base: Base, target_type: str) -> List[Base]:
    """Sucht nach Zielen (feindlich, neutral oder verbündet) basierend auf Typ."""
    if target_type == "enemy":
        return sorted(
            [b for b in game_state.bases if b.player != player_id and b.player != 0],
            key=lambda t: calculate_distance(base.position, t.position)
        )
    elif target_type == "neutral":
        return sorted(
            [b for b in game_state.bases if b.player == 0],
            key=lambda t: calculate_distance(base.position, t.position)
        )
    elif target_type == "ally":
        return sorted(
            [b for b in game_state.bases if b.player == player_id and b.uid != base.uid],
            key=lambda t: calculate_distance(base.position, t.position)
        )


def predict_enemy_behavior(enemy_bases: List[Base]) -> Base:
    """Sagt vorher, welches feindliche Ziel am wahrscheinlichsten angreift."""
    # Simple Heuristik: Gegner wird wahrscheinlich von der stärksten Basis aus angreifen
    return max(enemy_bases, key=lambda b: b.population, default=None)


def decide(game_state: GameState) -> List[PlayerAction]:
    """Entscheidet die Aktionen des Spielers basierend auf dem aktuellen Spielzustand."""
    player_id = game_state.game.player_id
    actions = []
    enemy_bases = [b for b in game_state.bases if b.player != player_id and b.player != 0]

    for base in game_state.bases:
        if base.player == player_id:
            # 1. Upgrade priorisieren
            if base.units_until_upgrade > 0 and base.population >= base.units_until_upgrade:
                actions.append(PlayerAction(base.uid, base.uid, base.units_until_upgrade))
                base.population -= base.units_until_upgrade
                continue

            # 2. Angreifen: Suche nach feindlichen Zielen
            enemy_targets = find_targets(game_state, player_id, base, "enemy")
            if enemy_targets:
                for target in enemy_targets:
                    required_bits = target.population + 1  # Angriff mit mindestens einem Bit mehr
                    if base.population >= required_bits:
                        actions.append(PlayerAction(base.uid, target.uid, required_bits))
                        base.population -= required_bits
                        break

            # 3. Expansion: Suche nach neutralen Basen
            neutral_targets = find_targets(game_state, player_id, base, "neutral")
            if neutral_targets and base.population >= 5:  # Mindestens 5 Einheiten für Eroberung
                actions.append(PlayerAction(base.uid, neutral_targets[0].uid, 5))
                base.population -= 5

            # 4. Verteidigung: Überschüssige Einheiten an verbündete Basen senden
            if base.population > base.max_population * 0.8:
                ally_targets = find_targets(game_state, player_id, base, "ally")
                if ally_targets:
                    transfer_amount = (base.population - base.max_population) // 2
                    if transfer_amount > 0:
                        actions.append(PlayerAction(base.uid, ally_targets[0].uid, transfer_amount))
                        base.population -= transfer_amount

    # 5. Präventive Verteidigung
    strongest_enemy = predict_enemy_behavior(enemy_bases)
    if strongest_enemy:
        for base in game_state.bases:
            if base.player == player_id:
                distance_to_enemy = calculate_distance(base.position, strongest_enemy.position)
                if distance_to_enemy < 10:  # Wenn ein Gegner nah ist
                    defensive_units = base.population // 2
                    actions.append(PlayerAction(base.uid, strongest_enemy.uid, defensive_units))

    return actions
