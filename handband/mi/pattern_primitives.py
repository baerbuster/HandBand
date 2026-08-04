"""
Pattern Primitives

Phase 1 of Musical Intelligence. The shared toolbox.
Every engine downstream composes from these five
functions. No musical opinion lives here — just pure
pattern-building utilities.

weighted_choice: pick one thing from a list, weighted.
density_calculator: how many events in a given space.
selected_patterns: how many sections to split a length
    into, biased by arousal via a Gaussian curve.
generate_variation: build a repetition pattern (AABA,
    ABCAB, etc.) driven by arousal and valence.
archetype_placer: place N items into positions using
    weighted selection without replacement.
"""

import random
import math


def weighted_choice(options, weight_list):
    """Pick one option from a weighted list."""
    return random.choices(options, weight_list, k=1)[0]


def density_calculator(length, scalar, emote_value, minimum=1):
    """How many events fit in a space. Never returns less than minimum."""
    return max(minimum, round(length * scalar * abs(emote_value)))


def selected_patterns(length, arousal, k, maximum=None):
    """
    Pick how many equal sections to divide a length into.
    High arousal favors more sections, low arousal fewer.
    k controls how sharply the Gaussian preference peaks.
    """
    length_list = [i for i in range(1, length + 1) if length % i == 0]
    if maximum is not None:
        length_list = [i for i in length_list if i <= maximum]
    upper = length_list[-1]
    center = 1 + (upper - 1) * arousal
    arousal_function = []

    for i in range(len(length_list)):
        distance = length_list[i] - center
        weight = math.exp(-0.5 * (distance / k) ** 2)
        arousal_function.append(weight)

    partition_number = weighted_choice(length_list, arousal_function)
    return partition_number


def generate_variation(partition_number, arousal, valence,
                       repeat_mult=10, return_mult=5,
                       chunk_mult=8, novelty_factor=0.1):
    """
    Build a repetition pattern like AABA or ABCAB.
    Arousal drives repetition and chunking.
    Valence drives return to earlier material.
    Novelty factor controls how eager it is to
    introduce new letters.
    """
    if partition_number == 1:
        return ['A']

    alphabet = [chr(65 + i) for i in range(partition_number)]

    repeat_strength = arousal
    return_strength = max(0, valence)
    chunk_strength = arousal

    pattern = [alphabet[0]]
    unlocked_count = 1

    for index in range(1, partition_number):
        weights = {}
        available = unlocked_count + 1 if unlocked_count < partition_number else unlocked_count
        for letter in alphabet[:available]:
            weights[letter] = 1.0

        # Repeating — favor staying on current letter
        prev_letter = pattern[-1]
        weights[prev_letter] = weights.get(prev_letter, 0) + repeat_strength * repeat_mult

        # Returning — favor letters seen earlier
        seen = set()
        for i in range(len(pattern) - 1):
            letter = pattern[i]
            if letter != prev_letter and letter not in seen:
                weights[letter] = weights.get(letter, 0) + return_strength * return_mult
                seen.add(letter)

        # Chunking — favor continuing recognized subsequences
        matched_positions = {}
        for chunk_len in range(len(pattern) - 1, 0, -1):
            suffix = pattern[-(chunk_len):]
            for start in range(len(pattern) - chunk_len):
                candidate = pattern[start:start + chunk_len]
                if candidate == suffix:
                    next_pos = start + chunk_len
                    if next_pos < len(pattern):
                        already_covered = False
                        for ms, ml in matched_positions.items():
                            if ms <= start < ms + ml:
                                already_covered = True
                                break
                        if not already_covered:
                            matched_positions[start] = chunk_len
                            continuation = pattern[next_pos]
                            weights[continuation] = weights.get(continuation, 0) + chunk_strength * chunk_mult * chunk_len

        # Novelty — chance to unlock the next letter
        if unlocked_count < partition_number:
            new_letter = alphabet[unlocked_count]
            novelty_boost = sum(weights.values()) * novelty_factor
            weights[new_letter] = weights.get(new_letter, 0) + novelty_boost

        options = list(weights.keys())
        w = [weights[o] for o in options]
        chosen = weighted_choice(options, w)
        pattern.append(chosen)

        if unlocked_count < partition_number and chosen == alphabet[unlocked_count]:
            unlocked_count += 1

    return pattern


def archetype_placer(N, weights, positions):
    """
    Place N items into available positions via weighted
    selection without replacement. Returns sorted.
    """
    placement = list(range(N))
    weights = weights.copy()
    positions = positions.copy()
    for i in range(N):
        chosen = weighted_choice(positions, weights)
        placement[i] = chosen
        chosen_index = positions.index(chosen)
        positions.pop(chosen_index)
        weights.pop(chosen_index)
    placement.sort()
    return placement