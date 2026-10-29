"""Single calculation engine for KPIs, tables and all chart types."""
from dataclasses import dataclass
import math
import pandas as pd
from studio.constants import NUMERIC_METHODS, NON_MEASURES, PRIVATE_COLUMNS, METHODS, LABELS
from studio.filters import apply_conditions, apply_filters, describe_filters


class IndicatorError(ValueError):
    pass


def numeric_columns(frame):
    return [c for c in frame if c not in NON_MEASURES and pd.api.types.is_numeric_dtype(frame[c])]


def public_columns(frame):
    return [c for c in frame if c not in PRIVATE_COLUMNS]


def scalar(frame, spec):
    method = spec['method']
    if method == 'count':
        return len(frame)
    if method == 'percentage':
        # The numerator is always restricted to the denominator's scope.
        denominator_frame = apply_conditions(frame, spec.get('denominator', []))
        denominator = len(denominator_frame)
        numerator = len(apply_conditions(denominator_frame, spec.get('numerator', [])))
        return 100.0 * numerator / denominator if denominator else None
    column = spec.get('value_column')
    if column not in frame:
        raise IndicatorError(f'Kolom nilai {column} tidak tersedia. Edit komponen dan pilih kolom yang tersedia.')
    values = frame[column]
    if method == 'count_filled':
        return int(values.notna().sum())
    if method == 'nunique':
        return int(values.nunique(dropna=True))
    if method in NUMERIC_METHODS:
        if column not in numeric_columns(frame):
            raise IndicatorError(f'{column} bukan ukuran numerik yang boleh dihitung dengan {METHODS[method]}.')
        if not values.notna().any():
            return None
        value = values.sum(min_count=1) if method == 'sum' else getattr(values, method)()
        return None if pd.isna(value) else float(value)
    raise IndicatorError('Metode indikator tidak dikenali.')


@dataclass
class Result:
    total: int | float | None
    table: pd.DataFrame
    rows: int
    explanation: str
    unavailable: str | None = None


def calculate(frame, spec, dimension=None, granularity='category'):
    total = scalar(frame, spec)
    if dimension:
        if dimension not in frame:
            raise IndicatorError(f'Kolom dimensi {dimension} tidak tersedia. Edit pemetaan komponen.')
        if dimension in PRIVATE_COLUMNS:
            raise IndicatorError('Identitas pribadi hanya digunakan untuk hitungan terisi/unik, bukan dimensi tampilan.')
        groups = frame[dimension]
        if granularity in ('day', 'month', 'year'):
            if not pd.api.types.is_datetime64_any_dtype(groups):
                raise IndicatorError('Dimensi tren harus berupa kolom tanggal.')
            groups = groups.dt.to_period({'day':'D', 'month':'M', 'year':'Y'}[granularity]).astype('string')
        groups = groups.astype('string').fillna('(Kosong)') if not pd.api.types.is_numeric_dtype(groups) else groups.fillna(float('-inf'))
        output = []
        for label, indices in groups.groupby(groups, sort=True).groups.items():
            output.append({'Kategori': '(Kosong)' if label == float('-inf') else label, 'Nilai': scalar(frame.loc[indices], spec)})
        table = pd.DataFrame(output, columns=['Kategori', 'Nilai'])
    else:
        table = pd.DataFrame([{'Kategori': 'Total', 'Nilai': total}])
    reason = None
    if frame.empty:
        reason = 'Tidak ada data sesuai filter.'
    elif total is None:
        reason = 'Penyebut nol; persentase tidak tersedia.' if spec['method'] == 'percentage' else 'Seluruh nilai kosong; tidak diubah menjadi nol.'
    return Result(total, table, len(frame), '', reason)


def count_pivot(frame, rows, columns):
    """Cross-tabulate record counts without changing the shared source frame."""
    if rows == columns:
        raise IndicatorError('Pilih kolom berbeda untuk baris dan kolom pivot.')
    for column in (rows, columns):
        if column not in frame:
            raise IndicatorError(f'Kolom pivot {column} tidak tersedia.')
        if column in PRIVATE_COLUMNS:
            raise IndicatorError('Identitas pribadi tidak boleh menjadi dimensi pivot.')
    if frame.empty:
        return pd.DataFrame(index=pd.Index([], name=rows),
                            columns=pd.Index([], name=columns), dtype='int64')
    # Include missing categories, just as calculate() does for chart dimensions.
    data = frame[[rows, columns]].astype('string').fillna('(Kosong)')
    total_label = 'Total'
    while any(data[column].eq(total_label).any() for column in (rows, columns)):
        total_label += ' keseluruhan'
    count_column = '_jumlah_record'
    while count_column in data:
        count_column += '_'
    data[count_column] = 1
    return pd.pivot_table(data, index=rows, columns=columns, values=count_column,
                          aggfunc='sum', fill_value=0, margins=True,
                          margins_name=total_label, observed=True)


def compute_component(bundle, design, component):
    dataset = component['dataset']
    frame = apply_filters(bundle.frame(dataset), dataset, design['filters'], component['local_filters'])
    dimension = None if component['kind'] in ('kpi', 'note') else component['dimension']
    result = calculate(frame, component, dimension, component['granularity'])
    scope = describe_filters(dataset, design['filters'], component['local_filters'])
    unit = '%' if component['method'] == 'percentage' else component['unit'] or 'tanpa satuan'
    value = f" ({component['value_column']})" if component['value_column'] else ''
    result.explanation = f"Sumber: {LABELS[dataset]}. Metode: {METHODS[component['method']]}{value}. Satuan: {unit}. Cakupan: {scope}. Record dalam cakupan: {len(frame)}."
    if component['method'] == 'percentage':
        result.explanation += f" Pembilang: {component['numerator'] or 'semua record'}; penyebut: {component['denominator'] or 'semua record dalam cakupan'}. Pembilang dibatasi pada cakupan penyebut."
    if dataset == 'pelayanan' and component['value_column'] == 'lama_proses':
        statuses = ', '.join(sorted(frame.status.dropna().unique())) or 'tidak ada'
        result.explanation += f' Status yang masuk hitungan: {statuses}.'
    if component['value_column'] == 'omset':
        result.explanation += f" Periode omzet: {component['period'] or 'tidak tersedia pada sumber'} ."
    return result


def format_id(value, decimals=0, unit=''):
    if value is None or pd.isna(value) or not math.isfinite(float(value)):
        return 'Tidak tersedia'
    text = f'{value:,.{decimals}f}'.replace(',', '#').replace('.', ',').replace('#', '.')
    if unit == 'Rp':
        return f'Rp{text}'
    return f'{text}%' if unit == '%' else f'{text} {unit}'.strip()
