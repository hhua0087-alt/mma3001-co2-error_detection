"""Post-inference evaluation using labels that are never inputs to prediction."""
import numpy as np
import pandas as pd


def evaluate_alarm_events(alarm, original_alarm, events):
    """Evaluate event hits, paired additions and elapsed delay after inference.

    Args:
        alarm: Boolean Series for the faulted test replay.
        original_alarm: Boolean Series from the unmodified replay at the same times.
        events: Separate dictionaries with event_id, sign, active and recovery indices.
    Returns:
        (summary, details): Event/reading fractions and per-event outcomes. An event
        needs one active alarm. A paired addition needs one same-time new alarm.
        Missed-event delay is None, never zero. Recovery alarms do not rescue misses.
    Raises:
        ValueError: There are no events or indices differ.
        KeyError: A labelled timestamp is not monitored.
    """
    if not events or not alarm.index.equals(original_alarm.index):
        raise ValueError("Require events and identically indexed alarm replays.")
    active_mask = pd.Series(False, index=alarm.index)
    recovery_mask = pd.Series(False, index=alarm.index)
    details = []
    for event in events:
        active = event["active"]
        active_mask.loc[active] = True
        recovery_mask.loc[event["recovery"]] = True
        hits = active[alarm.loc[active].to_numpy()]
        added = bool((alarm.loc[active] & ~original_alarm.loc[active]).any())
        delay = (hits[0]-active[0]).total_seconds()/60 if len(hits) else None
        details.append({"event_id": event["event_id"], "sign": event["sign"],
                        "detected": bool(len(hits)), "additional_alarm": added,
                        "first_alert_delay_minutes": delay})
    outside = ~active_mask & ~recovery_mask
    detected = sum(int(row["detected"]) for row in details)
    additional = sum(int(row["additional_alarm"]) for row in details)
    delays = [row["first_alert_delay_minutes"] for row in details if row["detected"]]
    summary = {"events": len(events), "detected": detected, "event_recall": detected/len(events),
               "paired_additional_events": additional,
               "paired_additional_event_fraction": additional/len(events),
               "reading_recall": float(alarm.loc[active_mask].mean()),
               "unmodified_test_alert_rate": float(original_alarm.mean()),
               "outside_fault_and_recovery_alert_rate": float(alarm.loc[outside].mean()) if outside.any() else None,
               "recovery_alert_rate": float(alarm.loc[recovery_mask].mean()) if recovery_mask.any() else None,
               "median_first_alert_delay_minutes": float(np.median(delays)) if delays else None}
    return summary, details


def score_development_events(alarm, clean_alarm, events):
    """Score separate development labels after inference; missed events incur unit delay cost."""
    additional, detected, costs = 0, 0, []
    for event in events:
        active = event["active"]
        hits = np.flatnonzero(alarm.loc[active].to_numpy())
        added = np.flatnonzero((alarm.loc[active] & ~clean_alarm.loc[active]).to_numpy())
        detected += int(len(hits) > 0)
        additional += int(len(added) > 0)
        costs.append(float(added[0]/len(active)) if len(added) else 1.0)
    return {"event_recall": detected/len(events), "additional_event_recall": additional/len(events),
            "capped_additional_delay_fraction": float(np.mean(costs))}

