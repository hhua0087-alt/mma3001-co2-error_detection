"""Optional real-data regression checks after notebooks 01 and 02 have completed."""
import json
from pathlib import Path
import pandas as pd
import pytest
from co2_project.project import get_run

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'results_summary/reference'


@pytest.fixture(scope='module')
def runs():
    try:return get_run(ROOT,'main'),get_run(ROOT,'input_comparison')
    except FileNotFoundError:pytest.skip('Run notebooks 01 and 02 with authorized data for integration checks.')


@pytest.mark.integration
@pytest.mark.parametrize('role,actual,reference,keys',[
    (0,'comparison_all_methods.csv','main_default.csv',['scenario','method']),
    (0,'prediction_quality.csv','main_quality.csv',['method','part']),
    (0,'test_sensitivity.csv','main_sensitivity.csv',['scenario','seed','magnitude_ppm','duration_readings','method']),
    (1,'controlled_default.csv','input_default.csv',['scenario','method']),
    (1,'prediction_quality.csv','input_quality.csv',['method','part']),
    (1,'test_sensitivity.csv','input_sensitivity.csv',['scenario','seed','magnitude_ppm','duration_readings','method'])])
def test_completed_metrics_match_reference(runs,role,actual,reference,keys):
    expected=pd.read_csv(REF/reference)
    current=pd.read_csv(runs[role]/actual)
    pd.testing.assert_frame_equal(current[expected.columns].sort_values(keys).reset_index(drop=True),
        expected.sort_values(keys).reset_index(drop=True),check_dtype=False,atol=1e-8,rtol=1e-9)


@pytest.mark.integration
def test_completed_weights_and_calibration_match_reference(runs):
    expected=json.loads((REF/'protocol.json').read_text(encoding='utf-8'))
    main=json.loads((runs[0]/'run_report.json').read_text(encoding='utf-8'))
    inputs=json.loads((runs[1]/'run_report.json').read_text(encoding='utf-8'))
    # Different raw/extracted file layouts must represent exactly the same model input.
    assert main['audit']['prepared_sha256']==expected['prepared_sha256']
    assert inputs['audit']['prepared_sha256']==expected['prepared_sha256']
    assert main['audit']['prepared_fingerprint_version']==expected['prepared_fingerprint_version']
    assert main['split_counts']==expected['split_counts']
    assert main['models']['history_neural']['weights_sha256']==expected['eight_input_weights_sha256']
    assert inputs['models']['environment_neural']['weights_sha256']==expected['six_input_weights_sha256']
    assert main['selection']['kappa']==expected['kappa'] and main['selection']['H']==expected['H']
    assert abs(inputs['calibration']['environment_neural_cusum']['h']-expected['six_input_cusum_h'])<1e-8
