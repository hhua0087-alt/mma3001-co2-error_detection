"""Two-sided CUSUM with label-free resets and validation-only calibration."""
import numpy as np
import pandas as pd

def cusum_series(residual,k,h,max_gap_minutes=20):
    """Accumulate two-sided residual shifts in time order; reset after crossing h or after a large gap.

    Args:
        residual: Finite signed residuals centered on their training mean.
        k: Nonnegative allowance per reading.
        h: Positive cumulative threshold.
    Returns:
        Series: Accumulated statistic before resets, not CO2 predictions or point residuals.
    Raises:
        ValueError: Invalid k/h or non-finite residuals."""
    if not 0<=k or not h>0 or not np.isfinite([k,h]).all():
        raise ValueError('CUSUM requires finite k>=0 and h>0.')
    if not np.isfinite(residual.to_numpy()).all():
        raise ValueError('CUSUM residuals must be finite.')
    scores=[]
    up=down=0.0
    previous=None
    for timestamp,value in residual.items():
        if previous is None or (timestamp-previous).total_seconds()/60>max_gap_minutes:
            up=down=0.0
        # Accumulate each direction separately; subtract allowance k at every step.
        up=max(0.0,up+float(value)-k)
        down=max(0.0,down-float(value)-k)
        score=max(up,down)
        scores.append(score)  # Determine the current alarm from the score before reset.
        if score>h:
            up=down=0.0      # Reset on the alarm, without reading fault-end labels.
        previous=timestamp
    return pd.Series(scores,index=residual.index)


def normalized_cusum(z,kappa,H,max_gap_minutes=20):
    """Causal two-sided CUSUM of centered, threshold-scaled NN residuals.

    z: finite Series with increasing unique UTC timestamps.
    kappa: nonnegative allowance in NN-threshold units.
    H: positive cumulative alarm threshold in the same scaled units.
    Alarms and >20-minute gaps reset state; event labels are never inputs.
    Returned upper/lower/score values are BEFORE an alarm-triggered reset.
    """
    if not np.isfinite([kappa, H]).all() or kappa < 0 or H <= 0:
        raise ValueError("Require finite kappa >= 0 and H > 0.")
    if not isinstance(z.index, pd.DatetimeIndex) or z.index.hasnans or z.index.tz is None:
        raise ValueError("Require a timezone-aware DatetimeIndex.")
    if not z.index.is_monotonic_increasing or not z.index.is_unique:
        raise ValueError("Timestamps must increase and be unique.")
    values = z.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("CUSUM input must be finite.")
    gaps = z.index.to_series().diff().dt.total_seconds().to_numpy()/60
    upper, lower, scores, alarms = np.zeros(len(z)), np.zeros(len(z)), np.zeros(len(z)), np.zeros(len(z), dtype=bool)
    up = down = 0.0
    for i, value in enumerate(values):
        if i == 0 or gaps[i] > max_gap_minutes:
            up = down = 0.0
        up = max(0.0, up + value - kappa)
        down = max(0.0, down - value - kappa)
        upper[i], lower[i] = up, down
        scores[i] = max(up, down)
        alarms[i] = scores[i] > H
        if alarms[i]:
            up = down = 0.0
    return pd.DataFrame({"upper": upper, "lower": lower, "score": scores, "alarm": alarms}, index=z.index)



def select_cusum_limit(residual,k,sigma,quantile=.99,initial_grid=None,allow_extension=False,max_gap_minutes=20):
    """Choose the first limit meeting an unmodified-validation alert budget.

    Args:
        residual: Centred validation residual Series in ppm, not test faults.
        k: Allowance in ppm per reading.
        sigma: Training residual SD in ppm, strictly positive.
        quantile: Budget convention; .99 permits ceil(1% of readings) alarms.
        initial_grid: Multipliers of training sigma; default .5 to 40.5 by .25.
        allow_extension: Extend the common grid in quarter-SD steps if infeasible.
        max_gap_minutes: Gap that resets the statistic, shared with inference.
    Returns:
        dict: h, validation_alerts, budget, initial_grid_feasible and trial records.
    Raises:
        ValueError: Invalid settings or no feasible limit without extension.
    """
    if not np.isfinite(sigma) or sigma<=0 or not 0<quantile<1 or len(residual)==0:
        raise ValueError('Require positive sigma, a nonempty validation series and 0<quantile<1.')
    grid=np.asarray(initial_grid if initial_grid is not None else np.arange(.5,40.5001,.25))
    if len(grid)==0 or not np.isfinite(grid).all() or (grid<=0).any():
        raise ValueError('CUSUM grid must contain finite positive multipliers.')
    budget=int(np.ceil((1-quantile)*len(residual)))
    trials=[];chosen=None
    for multiplier in grid:
        h=float(multiplier*sigma)
        alerts=int((cusum_series(residual,k,h,max_gap_minutes)>h).sum())
        trials.append(dict(h=h,validation_alerts=alerts))
        if alerts<=budget:chosen=(h,alerts);break
    initial=chosen is not None
    initial_trials=list(trials)
    if chosen is None and allow_extension:
        bound=float(residual.abs().sum())+sigma
        first=int(round(float(grid[-1])*4))+1
        last=int(np.ceil(bound/sigma*4))+1
        for quarter in range(first,last+1):
            h=float(quarter/4*sigma)
            alerts=int((cusum_series(residual,k,h,max_gap_minutes)>h).sum())
            trials.append(dict(h=h,validation_alerts=alerts))
            if alerts<=budget:chosen=(h,alerts);break
    if chosen is None:raise ValueError('No CUSUM threshold meets the validation budget.')
    return dict(h=chosen[0],validation_alerts=chosen[1],budget=budget,
                initial_grid_feasible=initial,trials=trials,initial_trials=initial_trials)
