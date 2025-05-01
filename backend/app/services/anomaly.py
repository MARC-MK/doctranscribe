from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


THRESH_Z = 3.0
THRESH_MOD_Z = 3.5
FACTOR_IQR = 1.5


def z_score(series: pd.Series) -> pd.Series:
    z = (series - series.mean()) / series.std(ddof=0)
    return z.abs() > THRESH_Z


def modified_z_score(series: pd.Series) -> pd.Series:
    median = series.median()
    mad = (series - median).abs().median()
    if mad == 0:
        return pd.Series([False] * len(series), index=series.index)
    mod_z = 0.6745 * (series - median).abs() / mad
    return mod_z > THRESH_MOD_Z


def iqr_method(series: pd.Series) -> pd.Series:
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - FACTOR_IQR * iqr
    upper = q3 + FACTOR_IQR * iqr
    return (series < lower) | (series > upper)


def isolation_forest(series: pd.Series) -> pd.Series:
    model = IsolationForest(contamination="auto", random_state=42)
    preds = model.fit_predict(series.to_frame())  # -1 anomaly, 1 normal
    return pd.Series(preds == -1, index=series.index)


ALGOS = {
    "z": z_score,
    "modified_z": modified_z_score,
    "iqr": iqr_method,
    "isolation_forest": isolation_forest,
}


def detect_anomalies(df: pd.DataFrame, numeric_cols: List[str] | None = None, methods: List[str] | None = None) -> pd.DataFrame:
    """Return df with anomaly boolean column and list of methods triggered."""
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if methods is None:
        methods = list(ALGOS.keys())

    anomalies_list: List[List[str]] = [[] for _ in range(len(df))]

    for method in methods:
        func = ALGOS[method]
        for col in numeric_cols:
            mask = func(df[col].astype(float))
            for idx in df[mask].index:
                anomalies_list[idx].append(method)

    df = df.copy()
    df["anomaly_methods"] = anomalies_list
    df["is_anomaly"] = df["anomaly_methods"].apply(bool)
    return df 