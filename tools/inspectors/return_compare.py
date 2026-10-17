"""RR04-RR05: pure return identity and full-range comparison, with no mapping claim."""

import hashlib

from tools.inspectors.observation_capture import fields, require
from tools.inspectors.origin_compare import compare_ranges


def reference_item(plan, origin, capture):
    fields(capture["return_reference"], "name sha256")
    target = plan["stop_at_historical_event_sequence"]
    require(type(target) is int and target > plan["restore_event_sequence"], "RETURN_REFERENCE")
    matches = [c for c in origin["comparisons"] if c["event_sequence"] == target]
    require(len(matches) == 1, "RETURN_REFERENCE")
    item = matches[0]
    require(item["state_sha256"] == capture["return_reference"]["sha256"], "RETURN_REFERENCE")
    return item


def validate_return(capture, states, restored, reference, historical, last_pair):
    sequence = capture["return_sequence"]
    require(
        type(sequence) is int and sequence == len(states) and sequence > last_pair,
        "RETURN_ORDER",
    )
    returned = states[-1]
    require(
        not returned.cpu.delay_slot
        and not reference.cpu.delay_slot
        and returned.cpu.pc == reference.cpu.pc == restored.cpu.gpr_low32[31]
        and returned.cpu.pc % 4 == 0,
        "RETURN_POINT",
    )
    require(
        hashlib.sha256(reference.data).hexdigest()
        == historical["against_resource"]["observed_sha256"],
        "RETURN_REFERENCE_RANGE",
    )
    return {
        "sequence": sequence,
        "historical_event_sequence": historical["event_sequence"],
        "historical_state_sha256": historical["state_sha256"],
        "pc_matches_entry_link_and_historical": True,
        "against_historical": compare_ranges(reference.data, returned.data),
        "against_entry": compare_ranges(restored.data, returned.data),
    }


def compare_writer_pairs(previous, current):
    """Compare validated changed-store metadata, independently of sequence numbering."""
    old = [p for p in previous["pairs"] if p["status"] == "consistent_changed_store"]
    new = [p for p in current["pairs"] if p["status"] == "consistent_changed_store"]
    require(len(old) == 1 and len(new) >= 1, "RETURN_CHANGED_PAIR")
    keys = (
        "instruction_class",
        "control_flow",
        "instruction_sha256",
        "relative_offset",
        "width",
        "comparison",
    )
    comparisons = []
    for pair in new:
        differing = [k for k in keys if pair[k] != old[0][k]]
        comparisons.append(
            {
                "previous_before_sequence": old[0]["before_sequence"],
                "current_before_sequence": pair["before_sequence"],
                "equal": not differing,
                "differing_fields": differing,
            }
        )
    return comparisons
