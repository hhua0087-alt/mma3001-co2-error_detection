"""Known-value and failure-case checks independent of the private course data."""
import json
import numpy as np
import pandas as pd
import pytest
from co2_project.data import prepare_environment_csv,make_features,chronological_split
from co2_project.faults import WindowPlanner,inject_fault
from co2_project.detectors import cusum_series,normalized_cusum,select_cusum_limit
from co2_project.models import fit_ols,predict_ols_features
from co2_project.evaluation import evaluate_alarm_events
from co2_project.project import find_project_root,resolve_data_csv,record_run,get_run


def observations(n=500):
    """Return manufactured channels; values do not come from the course dataset."""
    index=pd.date_range('2020-01-01',periods=n,freq='10min',tz='UTC')
    return pd.DataFrame({'Carbon dioxide':400.+np.arange(n)%17,'Temperature':20.+np.arange(n)/1000,
                         'Humidity':50.+np.arange(n)%7},index=index)


def test_features_are_causal_and_preserve_lag_meaning():
    frame=observations(40);before=make_features(frame)
    changed=frame.copy();changed.loc[frame.index[21]:,'Carbon dioxide']+=300
    changed.loc[frame.index[21]:,'Temperature']+=4
    after=make_features(changed)
    pd.testing.assert_frame_equal(before.iloc[:21],after.iloc[:21])
    assert before.co2_lag6.iloc[6]==frame['Carbon dioxide'].iloc[0]
    assert before.co2_lag1.iloc[6]==frame['Carbon dioxide'].iloc[5]


def test_split_excludes_six_readings_after_a_large_gap():
    frame=observations()
    index=frame.index.to_list()
    for i in range(250,len(index)):index[i]+=pd.Timedelta(hours=2)
    frame.index=pd.DatetimeIndex(index)
    result=chronological_split(frame,minimum_rows=20)
    assert not frame.index[250:256].isin(result['eligible']).any()
    assert result['train'][-1]<result['validation'][0]<result['test'][0]


def test_preparation_deduplicates_but_rejects_conflicts(tmp_path):
    rows=[{'sensor_id':'toy','timestamp_utc':str(t),'variable':v,'value':value}
          for t in pd.date_range('2020-01-01',periods=3,freq='10min',tz='UTC')
          for v,value in [('Carbon dioxide',400),('Temperature',20),('Humidity',50)]]
    path=tmp_path/'toy.csv'
    pd.DataFrame(rows+[rows[0]]).to_csv(path,index=False)
    frame,audit=prepare_environment_csv(path,'toy',minimum_rows=2)
    assert len(frame)==3 and audit['identical_duplicates_removed']==1
    pd.DataFrame(rows+[{**rows[0],'value':401}]).to_csv(path,index=False)
    with pytest.raises(ValueError,match='Conflicting'):prepare_environment_csv(path,'toy',2)


@pytest.mark.parametrize('fault',[ 'missing_column','missing_channel','nonfinite','invalid_time'])
def test_preparation_rejects_invalid_data(tmp_path,fault):
    frame=pd.DataFrame({'sensor_id':['toy']*3,'timestamp_utc':['2020-01-01']*3,
                        'variable':['Carbon dioxide','Temperature','Humidity'],'value':[400.,20.,50.]})
    if fault=='missing_column':frame=frame.drop(columns='value')
    elif fault=='missing_channel':frame=frame.iloc[:2]
    elif fault=='nonfinite':frame.loc[0,'value']=np.inf
    else:frame.loc[0,'timestamp_utc']='not-a-timestamp'
    path=tmp_path/'toy.csv';frame.to_csv(path,index=False)
    with pytest.raises(ValueError):prepare_environment_csv(path,'toy',1)


@pytest.mark.parametrize('kind,expected',[('spike',[60.]),('drift',[20.,40.,60.]),('bias',[60.,60.,60.])])
def test_fault_profiles_modify_only_co2(kind,expected):
    frame=observations(10);saved=frame.copy()
    active=frame.index[2:2+len(expected)]
    events=[dict(event_id=1,sign=-1,active=active,recovery=frame.index[6:8])]
    modified,offset=inject_fault(frame,events,kind,60.)
    np.testing.assert_allclose(offset.loc[active],-np.array(expected))
    pd.testing.assert_frame_equal(frame,saved)
    pd.testing.assert_frame_equal(frame[['Temperature','Humidity']],modified[['Temperature','Humidity']])


def test_window_plan_is_reproducible_and_returned_arrays_are_copied():
    frame=observations(700);split=pd.Series('test',index=frame.index)
    planner=WindowPlanner(frame,split,recovery_readings=3)
    a=planner.plan(4,3,7);b=planner.plan(4,3,7)
    assert [(list(e['active']),e['sign']) for e in a]==[(list(e['active']),e['sign']) for e in b]
    a[0]['sign']*=-1
    assert a[0]['sign']!=planner.plan(4,3,7)[0]['sign']
    with pytest.raises(ValueError):planner.plan(0,3,7)
    with pytest.raises(ValueError):planner.plan(4,3,7,partition='train')
    with pytest.raises(ValueError):planner.plan(600,3,7)


def test_cusum_known_accumulation_alarm_reset_and_gap_reset():
    index=pd.date_range('2020-01-01',periods=8,freq='10min',tz='UTC')
    trace=normalized_cusum(pd.Series([.25]*8,index=index),.1,1.)
    assert not trace.alarm.iloc[:6].any() and trace.alarm.iloc[6]
    assert np.isclose(trace.score.iloc[7],.15)
    gaps=pd.DatetimeIndex(['2020-01-01T00:00Z','2020-01-01T00:10Z','2020-01-01T01:00Z'])
    np.testing.assert_allclose(cusum_series(pd.Series([.5]*3,index=gaps),0.,2.),[.5,1.,.5])


def test_scaling_preserves_alarms_and_scores():
    index=pd.date_range('2020-01-01',periods=30,freq='10min',tz='UTC')
    residual=pd.Series(np.sin(np.arange(30))*14,index=index)
    old=cusum_series(residual,1.2,32.)
    scaled=normalized_cusum(residual/8.,1.2/8.,32./8.)
    np.testing.assert_allclose(old,scaled.score*8.)
    np.testing.assert_array_equal(old>32.,scaled.alarm)


@pytest.mark.parametrize('k,h',[(-1.,1.),(0.,0.),(np.nan,1.),(0.,np.inf)])
def test_invalid_cusum_parameters_are_rejected(k,h):
    residual=pd.Series([0.],index=pd.date_range('2020-01-01',periods=1,tz='UTC'))
    with pytest.raises(ValueError):cusum_series(residual,k,h)
    with pytest.raises(ValueError):normalized_cusum(residual,k,h)


def test_validation_grid_extension_is_explicit():
    r=pd.Series([1.]*20,index=pd.date_range('2020-01-01',periods=20,freq='10min',tz='UTC'))
    with pytest.raises(ValueError):select_cusum_limit(r,0.,1.,initial_grid=[.5],allow_extension=False)
    choice=select_cusum_limit(r,0.,1.,initial_grid=[.5],allow_extension=True)
    assert not choice['initial_grid_feasible'] and choice['validation_alerts']<=choice['budget']


def test_event_hits_additions_and_recovery_are_distinct():
    index=pd.date_range('2020-01-01',periods=8,freq='10min',tz='UTC')
    events=[dict(event_id=1,sign=1,active=index[1:3],recovery=index[3:5]),
            dict(event_id=2,sign=-1,active=index[5:7],recovery=index[7:])]
    alarm=pd.Series([False,True,False,True,False,False,False,True],index=index)
    clean=pd.Series([False,True,False,False,False,False,False,False],index=index)
    metrics,detail=evaluate_alarm_events(alarm,clean,events)
    assert metrics['detected']==1 and metrics['paired_additional_events']==0
    assert metrics['reading_recall']==.25
    assert detail[1]['first_alert_delay_minutes'] is None


def test_ols_known_linear_solution_and_rank_failure():
    x=pd.DataFrame({'x':np.arange(20,dtype=float),'z':np.sin(np.arange(20))})
    y=3.+2*x.x-4*x.z
    model=fit_ols(x,y)
    np.testing.assert_allclose(predict_ols_features(model,x),y,atol=1e-10)
    with pytest.raises(ValueError):fit_ols(pd.DataFrame({'x':x.x,'copy':x.x}),y)


def test_project_paths_and_completed_run_integrity(tmp_path,monkeypatch):
    (tmp_path/'src/co2_project').mkdir(parents=True)
    (tmp_path/'config').mkdir();(tmp_path/'config/study.json').write_text('{}')
    (tmp_path/'notebooks').mkdir()
    assert find_project_root(tmp_path/'notebooks')==tmp_path
    monkeypatch.delenv('CO2_DATA_CSV',raising=False)
    with pytest.raises(FileNotFoundError):resolve_data_csv(tmp_path)
    run=tmp_path/'results/main/toy';run.mkdir(parents=True)
    (run/'run_report.json').write_text(json.dumps({'source_sha256':'manufactured'}))
    record_run(tmp_path,'main',run)
    assert get_run(tmp_path,'main')==run
    (run/'run_report.json').write_text('{}')
    with pytest.raises(ValueError,match='changed'):get_run(tmp_path,'main')
