"""Verify the raw JSON extraction contract with manufactured input only."""
import json
import pandas as pd
import pytest
from co2_project.extraction import measurements,extract
from co2_project.data import prepare_environment_csv


def raw_record():
    """Return one synthetic raw row carrying all three required channels."""
    payload=[{'variable':{'name':name,'unit':unit},'values':[{'time':1577836800,'value':value}]}
             for name,unit,value in [('Carbon dioxide','ppm',400),('Temperature','C',20),('Humidity','%',50)]]
    return {'id':'synthetic-1','sensorid':'toy','jsondata':json.dumps(payload)}


def test_json_rows_and_variable_filter():
    records=list(measurements(raw_record()))
    assert len(records)==3 and records[0]['timestamp_utc']=='2020-01-01T00:00:00+00:00'
    assert len(list(measurements(raw_record(),'Carbon dioxide')))==1
    with pytest.raises(ValueError):list(measurements({**raw_record(),'jsondata':'broken'}))


def test_stream_extract_matches_preparation_schema(tmp_path):
    source=tmp_path/'raw.csv';output=tmp_path/'extracted.csv'
    pd.DataFrame([raw_record()]).to_csv(source,index=False)
    before=source.read_bytes()
    extract(source,output,'toy',None,100,False)
    prepared,audit=prepare_environment_csv(output,'toy',1)
    assert len(prepared)==1 and prepared['Carbon dioxide'].iloc[0]==400
    assert source.read_bytes()==before
    with pytest.raises(FileExistsError):extract(source,output,'toy',None,100,False)


def test_extractor_never_overwrites_source(tmp_path):
    source=tmp_path/'raw.csv';pd.DataFrame([raw_record()]).to_csv(source,index=False)
    before=source.read_bytes()
    with pytest.raises(ValueError,match='must differ'):extract(source,source,'toy',None,100,True)
    assert source.read_bytes()==before
