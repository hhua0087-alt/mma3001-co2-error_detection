"""Tables and plots connecting the saved experiment to the report's conclusions."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

METHODS=['change_rule','history_regression','history_tree','history_neural','history_neural_cusum','nn_threshold_cusum']
FOCUS=['history_neural','history_neural_cusum','nn_threshold_cusum']


def magnitude_summary(sensitivity,long_duration=24):
    """Pool three placements at a fixed duration, retaining raw and paired hits.

    Args:
        sensitivity: Saved six-detector test_sensitivity.csv DataFrame.
        long_duration: Drift/bias reading count; spikes always last one reading.
    Returns:
        DataFrame: Counts and observed per-seed recall range, not confidence limits.
    """
    common=sensitivity[(sensitivity.scenario=='spike')|(sensitivity.duration_readings==long_duration)].copy()
    common['recall']=common.detected/common.events
    return common.groupby(['scenario','magnitude_ppm','method'],as_index=False).agg(
        events=('events','sum'),detected=('detected','sum'),
        paired_additional_events=('paired_additional_events','sum'),
        mean_recall=('recall','mean'),min_seed_recall=('recall','min'),max_seed_recall=('recall','max'))


def seed_table(sensitivity,magnitude=60,long_duration=24):
    """Show each fault placement separately under common magnitude and duration.

    Args:
        sensitivity: Saved sensitivity DataFrame.
        magnitude: Absolute injected offset in ppm, final offset for a drift.
        long_duration: Number of active drift/bias readings.
    Returns:
        DataFrame: Event hits and denominators for every detector and seed.
    """
    return sensitivity[(sensitivity.magnitude_ppm==magnitude)&
                       ((sensitivity.scenario=='spike')|(sensitivity.duration_readings==long_duration))][
        ['scenario','method','seed','events','detected','paired_additional_events']].sort_values(['scenario','method','seed'])


def plot_magnitude_sensitivity(sensitivity,long_duration=24):
    """Plot the three NN alarm rules with observed placement ranges.

    Args:
        sensitivity: Saved six-detector sensitivity DataFrame.
        long_duration: Drift/bias length held fixed across amplitudes.
    Returns:
        matplotlib.figure.Figure: Three panels; error bars are min/max, not CIs.
    """
    table=magnitude_summary(sensitivity,long_duration)
    fig,axes=plt.subplots(1,3,figsize=(11,3.8),sharey=True,layout='constrained')
    labels=['NN point','Original CUSUM','Selected CUSUM']
    for ax,kind in zip(axes,['spike','drift','bias']):
        for key,label,marker in zip(FOCUS,labels,['o','s','^']):
            d=table[(table.scenario==kind)&(table.method==key)].sort_values('magnitude_ppm')
            mean=d.mean_recall.to_numpy()*100
            low=d.min_seed_recall.to_numpy()*100;high=d.max_seed_recall.to_numpy()*100
            ax.errorbar(d.magnitude_ppm,mean,yerr=[mean-low,high-mean],marker=marker,capsize=3,label=label)
        ax.set(title=kind.capitalize(),xlabel='Injected magnitude (ppm)',ylim=(-5,105),xticks=[20,40,60])
        ax.grid(alpha=.2)
    axes[0].set_ylabel('Event recall (%)')
    axes[0].legend(fontsize=8)
    return fig
