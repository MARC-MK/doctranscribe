import pandas as pd
from app.services import anomaly as an


def test_z_score():
    s = pd.Series([1, 1, 1, 10])
    mask = an.z_score(s)
    assert mask.iloc[-1] is True


def test_modified_z():
    s = pd.Series([1, 1, 1, 10])
    mask = an.modified_z_score(s)
    assert mask.iloc[-1] is True


def test_iqr():
    s = pd.Series([1, 1, 1, 10])
    mask = an.iqr_method(s)
    assert mask.iloc[-1] is True


def test_isolation_forest():
    s = pd.Series([1, 1, 1, 10])
    mask = an.isolation_forest(s)
    assert mask.iloc[-1] is True


def test_detect_anomalies():
    df = pd.DataFrame({"measurement": [1, 1, 1, 10]})
    out = an.detect_anomalies(df, numeric_cols=["measurement"], methods=["z", "iqr"])
    assert out.loc[3, "is_anomaly"] is True
    assert set(out.loc[3, "anomaly_methods"]) == {"z", "iqr"} 