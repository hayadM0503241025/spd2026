"""Single calculation engine for KPIs, tables and all chart types."""
from dataclasses import dataclass, field
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


@dataclass
class PivotResult(Result):
    cells: pd.DataFrame = field(default_factory=pd.DataFrame)


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


def pivot_labels(frame, column, granularity='category'):
    if column not in frame:
        raise IndicatorError(f'Kolom dimensi pivot {column} tidak tersedia. Edit pemetaan pivot.')
    if column in PRIVATE_COLUMNS:
        raise IndicatorError('Identitas pribadi tidak boleh menjadi dimensi pivot.')
    values = frame[column]
    if granularity != 'category':
        if granularity not in ('day','month','year') or not pd.api.types.is_datetime64_any_dtype(values):
            raise IndicatorError('Pengelompokan waktu pivot membutuhkan kolom tanggal.')
        values = values.dt.to_period({'day':'D','month':'M','year':'Y'}[granularity])
    return values.astype('string').fillna('(Kosong)')


def calculate_pivot(frame, spec, rows, columns, row_granularity='category', column_granularity='category'):
    if rows == columns:
        raise IndicatorError('Pilih kolom berbeda untuk baris dan kolom pivot.')
    row_values = pivot_labels(frame, rows, row_granularity).reset_index(drop=True)
    column_values = pivot_labels(frame, columns, column_granularity).reset_index(drop=True)
    total = scalar(frame, spec)
    if frame.empty:
        return PivotResult(total, pd.DataFrame(), 0, '', 'Tidak ada data sesuai filter.')
    if row_values.nunique() * column_values.nunique() > 25000:
        raise IndicatorError('Pivot terlalu besar. Pilih kategori yang lebih ringkas atau persempit filter.')
    total_label = 'Total'
    while row_values.eq(total_label).any() or column_values.eq(total_label).any():
        total_label += ' keseluruhan'
    data = pd.DataFrame({'Baris':row_values, 'Kolom':column_values, 'Record':range(len(frame))})
    # Each cell AND each margin calls the same scalar engine as a KPI. In
    # particular, means, distinct counts and percentages are recalculated
    # from source records rather than added from already aggregated cells.
    table = pd.pivot_table(data, index='Baris', columns='Kolom', values='Record',
                          aggfunc=lambda positions: scalar(frame.iloc[positions.to_numpy(dtype='int64')], spec),
                          margins=True, margins_name=total_label, observed=True, dropna=False,
                          fill_value=0 if spec['method'] in ('count','count_filled','nunique') else None)
    row_order = calculate(frame, {'method':'count'}, rows, row_granularity).table.Kategori.map(str).tolist()
    column_order = calculate(frame, {'method':'count'}, columns, column_granularity).table.Kategori.map(str).tolist()
    table = table.reindex(index=row_order+[total_label], columns=column_order+[total_label])
    table.index.name, table.columns.name = rows, columns
    body = table.iloc[:-1, :-1].rename_axis(index='Baris', columns='Kolom')
    cells = body.reset_index().melt(id_vars='Baris', var_name='Kolom', value_name='Nilai')
    cells['Nilai'] = pd.to_numeric(cells.Nilai)
    unavailable = None if total is not None else ('Penyebut nol; persentase tidak tersedia.'
                    if spec['method']=='percentage' else 'Seluruh nilai kosong; tidak diubah menjadi nol.')
    return PivotResult(total, table, len(frame), '', unavailable, cells)


def compute_component(bundle, design, component):
    dataset = component['dataset']
    frame = apply_filters(bundle.frame(dataset), dataset, design['filters'], component['local_filters'])
    if component['kind'] == 'pivot':
        result = calculate_pivot(frame, component, component['dimension'], component['pivot']['column'],
                                 component['granularity'], component['pivot']['granularity'])
    else:
        dimension = None if component['kind'] in ('kpi', 'note') else component['dimension']
        result = calculate(frame, component, dimension, component['granularity'])
    scope = describe_filters(dataset, design['filters'], component['local_filters'])
    unit = '%' if component['method'] == 'percentage' else component['unit'] or 'tanpa satuan'
    value = f" ({component['value_column']})" if component['value_column'] else ''
    result.explanation = f"Sumber: {LABELS[dataset]}. Metode: {METHODS[component['method']]}{value}. Satuan: {unit}. Cakupan: {scope}. Record dalam cakupan: {len(frame)}."
    if component['kind'] == 'pivot':
        result.explanation += f" Baris pivot: {component['dimension']}; kolom pivot: {component['pivot']['column']}. Total dihitung ulang dari record sumber dalam cakupan. Grafik memakai sel pivot tanpa baris/kolom Total."
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
