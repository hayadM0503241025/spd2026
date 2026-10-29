"""Deterministic preparation rules; no editing of the reference workbook."""
from datetime import date
import re
import numbers
import pandas as pd


def clean_text(value):
    if value is None or pd.isna(value):
        return pd.NA
    text = re.sub(r'\s+', ' ', str(value)).strip()
    return text if text else pd.NA


def parse_number(value):
    if value is None or pd.isna(value):
        return float('nan')
    if isinstance(value, numbers.Number):
        return float(value)
    text = str(value).strip().replace('Rp', '').replace(' ', '')
    if ',' in text:
        text = text.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'-?\d{1,3}(\.\d{3})+', text):
        text = text.replace('.', '')
    return pd.to_numeric(text, errors='coerce')


def ages_on(dates: pd.Series, reference: date) -> pd.Series:
    values = pd.to_datetime(dates, errors='coerce')
    before_birthday = (values.dt.month > reference.month) | (
        (values.dt.month == reference.month) & (values.dt.day > reference.day))
    ages = reference.year - values.dt.year - before_birthday.astype(int)
    return ages.where(values.notna() & (values <= pd.Timestamp(reference)) & (ages <= 120)).astype('Int64')


def age_groups(ages: pd.Series) -> pd.Series:
    return pd.cut(ages, bins=[-1, 14, 59, 120], labels=['0–14 tahun', '15–59 tahun', '60+ tahun']).astype('string')


def valid_coordinates(frame: pd.DataFrame) -> pd.Series:
    if not {'latitude', 'longitude'} <= set(frame.columns):
        return pd.Series(False, index=frame.index)
    lat = pd.to_numeric(frame.latitude, errors='coerce')
    lon = pd.to_numeric(frame.longitude, errors='coerce')
    return lat.between(-90, 90) & lon.between(-180, 180)


def identity_tokens(series: pd.Series, prefix: str):
    """Numeric Excel identities are suspect; never fabricate missing digits."""
    valid = series.map(lambda x: isinstance(x, str) and bool(re.fullmatch(r'\d{16}', x.strip())))
    lookup = {}
    output = []
    for value, ok in zip(series, valid):
        if not ok:
            output.append(pd.NA)
            continue
        raw = value.strip()
        if raw not in lookup:
            lookup[raw] = f'{prefix}-{len(lookup) + 1:06d}'
        output.append(lookup[raw])
    return pd.Series(output, index=series.index, dtype='string'), int((~valid & series.notna()).sum())


def profile(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{
        'Kolom': c, 'Tipe': str(frame[c].dtype),
        'Kosong': int(frame[c].isna().sum()),
        'Nilai unik terisi': int(frame[c].nunique()),
    } for c in frame.columns])
