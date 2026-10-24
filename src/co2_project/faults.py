"""Reproducible finite additive faults; original references stay outside inference."""
import json
import numpy as np
import pandas as pd
from .project import file_sha256

def _plan_windows(original,split,duration,count,seed,partition="test",max_gap_minutes=20,recovery_readings=30):
    """Plan test events and recovery indices. duration/count are positive integers; seed controls locations/signs.

    Returns:
        list[dict]: event_id, sign, active and recovery.
    Raises:
        ValueError: Invalid counts or insufficient separated continuous windows."""
    if type(duration) is not int or type(count) is not int or duration < 1 or count < 1:
        raise ValueError('Reading counts, event counts and minimum_rows must be positive integers.')
    if partition not in ("test", "validation"):
        raise ValueError("Only validation or test fault copies are supported.")
    positions = np.flatnonzero(split.to_numpy()==partition)
    candidates = []
    for start in range(6,len(positions)-duration-recovery_readings+1):
        context = positions[start-6:start+duration+recovery_readings]
        if not np.all(np.diff(context)==1):
            continue
        times = original.index[context]
        if (times.to_series().diff().dt.total_seconds().dropna()/60<=max_gap_minutes).all():
            candidates.append(start)
    slots,next_allowed = [],0
    for start in candidates:
        if start>=next_allowed:
            slots.append(start)
            next_allowed=start+duration+recovery_readings
    if count<1 or duration<1 or len(slots)<count:
        raise ValueError(f"Only {len(slots)} usable windows found; reduce event count or duration.")
    rng=np.random.default_rng(seed)
    chosen=sorted(rng.choice(slots,size=count,replace=False).tolist())
    events=[]
    for event_id,start in enumerate(chosen,1):
        active=original.index[positions[start:start+duration]]
        recovery=original.index[positions[start+duration:start+duration+recovery_readings]]
        events.append({"event_id":event_id,"sign":int(rng.choice([-1,1])),
                       "active":active,"recovery":recovery})
    return events


def write_scenario(name,observed,offsets,events,*,original,split,run_dir,fault_seed=42,recovery_readings=30,source_hash=""):
    # Store the evaluation reference separately; detectors never receive it.
    """Save an observation copy, ppm offsets and separate evaluation labels; return a scenario dictionary. Detectors receive no labels."""
    reference=pd.DataFrame({"original_co2_ppm":original["Carbon dioxide"],
                            "offset_ppm":offsets,"event_id":0},index=original.index)
    for event in events:
        reference.loc[event["active"],"event_id"]=event["event_id"]
    assert (offsets.loc[split!="test"]==0).all()
    pd.testing.assert_frame_equal(observed.loc[split!="test"],original.loc[split!="test"])
    pd.testing.assert_frame_equal(observed.drop(columns="Carbon dioxide"),original.drop(columns="Carbon dioxide"))
    np.testing.assert_allclose(observed["Carbon dioxide"]-original["Carbon dioxide"],offsets,atol=1e-10,rtol=0)
    folder=run_dir/"fault_data"/name
    folder.mkdir(parents=True,exist_ok=False)
    observations=observed.reset_index().copy()
    observations["split"]=split.to_numpy()
    observations.to_csv(folder/"observations.csv",index=False)
    reference.to_csv(folder/"reference_labels.csv")
    events_saved=[{"event_id":e["event_id"],"sign":e["sign"],
                   "active_timestamps_utc":[t.isoformat() for t in e["active"]],
                   "recovery_timestamps_utc":[t.isoformat() for t in e["recovery"]]} for e in events]
    manifest={"kind":name,"events":events_saved,"source_sha256":source_hash,
              "fault_seed":fault_seed,"recovery_readings":recovery_readings,
              "note":'Only CO2 bias is simulated; the original health status is unknown.'}
    (folder/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(name,":",len(events),'events; only test copies are modified, and evaluation references are stored separately.')
    return {"name":name,"observations":observed,"reference":reference,"events":events,"folder":folder}



class WindowPlanner:
    """Cache fixed plans by duration, count, fault seed and partition.

    Args:
        original: Complete UTC-indexed sensor frame.
        split: Chronological train/validation/test row labels.
        max_gap_minutes: Continuity cutoff in minutes.
        recovery_readings: Unmodified readings reserved after every event.
    """
    def __init__(self,original,split,max_gap_minutes=20,recovery_readings=30):
        self.original,self.split=original,split
        self.max_gap_minutes,self.recovery_readings=max_gap_minutes,recovery_readings
        self._cache={}

    def plan(self,duration,count,seed,partition='test'):
        """Return copied event dictionaries; seed controls placement and sign.

        Args:
            duration: Positive active reading count, not elapsed minutes.
            count: Positive number of separated events.
            seed: Fault placement RNG seed.
            partition: 'test' or 'validation'; never 'train'.
        Returns:
            list[dict]: event_id, sign, active timestamps and recovery timestamps.
        Raises:
            ValueError: Invalid settings or insufficient continuous windows.
        """
        key=(duration,count,seed,partition)
        if key not in self._cache:
            self._cache[key]=_plan_windows(self.original,self.split,duration,count,seed,partition,
                                         self.max_gap_minutes,self.recovery_readings)
        return [{**e,'active':e['active'].copy(),'recovery':e['recovery'].copy()} for e in self._cache[key]]

def inject_fault(original,events,kind,magnitude_ppm):
    """Modify a copy of CO2 only; retain the original frame unchanged.

    Args:
        original: Observations with a Carbon dioxide column in ppm.
        events: Fixed event plans; signs are +1 or -1.
        kind: 'spike', 'drift' or 'bias'.
        magnitude_ppm: Positive absolute offset, final offset for a drift ramp.
    Returns:
        (observed, offsets): Faulted frame and signed offsets Series in ppm.
    Raises:
        ValueError: Invalid type/magnitude, overlapping events or a multi-reading spike.
        KeyError: An event timestamp is absent.
    """
    if kind not in ('spike','drift','bias') or not np.isfinite(magnitude_ppm) or magnitude_ppm<=0:
        raise ValueError('Require a known fault type and positive finite magnitude.')
    offsets=pd.Series(0.0,index=original.index)
    used=set()
    for event in events:
        active=event['active']
        if len(active)==0 or (kind=='spike' and len(active)!=1) or event['sign'] not in (-1,1):
            raise ValueError('Check active reading count and event sign.')
        if used.intersection(active):raise ValueError('Fault windows overlap.')
        used.update(active)
        profile=np.arange(1,len(active)+1)/len(active) if kind=='drift' else np.ones(len(active))
        offsets.loc[active]=event['sign']*magnitude_ppm*profile
    observed=original.copy()
    observed['Carbon dioxide']+=offsets
    return observed,offsets
