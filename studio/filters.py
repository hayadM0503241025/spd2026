"""Pure filters. A dashboard mapping is explicit for every target dataset."""
import pandas as pd
from copy import deepcopy
from studio.constants import PRIVATE_COLUMNS


class FilterError(ValueError):
    pass


def infer_kind(series):
    if pd.api.types.is_datetime64_any_dtype(series):
        return 'date'
    if pd.api.types.is_numeric_dtype(series):
        return 'number'
    return 'category'


def filter_columns(bundle, existing=()):
    """Column choices include their explicit dataset scope, never inferred aliases."""
    options={}
    for dataset in bundle.ids:
        frame=bundle.frame(dataset)
        for column in frame:
            if column in PRIVATE_COLUMNS or not frame[column].notna().any():
                continue
            kind=infer_kind(frame[column])
            key=f'{column}:{kind}'
            if key not in options:
                options[key]={'label':column.replace('_',' ').capitalize(),'kind':kind,'mapping':{}}
            options[key]['mapping'][dataset]=column
    for rule in existing:
        if not any(rule['kind']==option['kind'] and rule['mapping']==option['mapping'] for option in options.values()):
            options['saved:'+rule['id']]={k:deepcopy(rule[k]) for k in ('label','kind','mapping')}
    return options


def select_filter_columns(existing, selected, options, create_id):
    """Changing available filter columns preserves values/IDs of retained rules."""
    output=[]
    for key in selected:
        option=options[key]
        old=next((r for r in existing if r['kind']==option['kind'] and r['mapping']==option['mapping']),None)
        if old is not None:
            output.append(deepcopy(old))
        else:
            output.append({'id':create_id(),**deepcopy(option),'value':[] if option['kind']=='category' else None})
    return output


def condition_mask(frame, condition):
    column = condition['column']
    if column not in frame:
        raise FilterError(f'Kolom {column} tidak tersedia.')
    series = frame[column]
    operator = condition['operator']
    value = condition.get('value')
    if operator == 'equals':
        mask = series.eq(value)
    elif operator == 'not_equals':
        mask = series.ne(value) & series.notna()
    elif operator == 'in':
        mask = series.isin(value)
    elif operator == 'not_null':
        mask = series.notna()
    elif operator == 'is_null':
        mask = series.isna()
    elif operator == 'gte':
        mask = series.ge(value)
    elif operator == 'lte':
        mask = series.le(value)
    else:
        raise FilterError('Kondisi perhitungan tidak dikenali.')
    return mask.fillna(False)


def apply_conditions(frame, conditions):
    output = frame.copy(deep=True)
    for condition in conditions:
        output = output.loc[condition_mask(output, condition)].copy()
    return output


def filter_is_active(rule):
    value = rule.get('value')
    return value is not None and value != []


def apply_rule(frame, column, rule):
    if column not in frame:
        raise FilterError(f'Pemetaan filter menunjuk kolom yang hilang: {column}.')
    if not filter_is_active(rule):
        return frame.copy(deep=True)
    series = frame[column]
    value = rule['value']
    if rule['kind'] == 'category':
        mask = series.astype('string').isin(value)
    elif rule['kind'] == 'number':
        if not pd.api.types.is_numeric_dtype(series):
            raise FilterError(f'{column} bukan kolom angka.')
        mask = series.between(value[0], value[1])
    elif rule['kind'] == 'date':
        if not pd.api.types.is_datetime64_any_dtype(series):
            raise FilterError(f'{column} bukan kolom tanggal.')
        mask = series.between(pd.Timestamp(value[0]), pd.Timestamp(value[1]))
    else:
        raise FilterError('Jenis filter tidak dikenali.')
    return frame.loc[mask.fillna(False)].copy(deep=True)


def apply_filters(frame, dataset, global_filters=(), local_filters=()):
    output = frame.copy(deep=True)
    for rule in global_filters:
        column = rule['mapping'].get(dataset)
        if column is not None:
            output = apply_rule(output, column, rule)
    for rule in local_filters:
        output = apply_rule(output, rule['column'], rule)
    return output


def describe_filters(dataset, global_filters=(), local_filters=()):
    descriptions = []
    for rule in global_filters:
        if dataset in rule['mapping'] and filter_is_active(rule):
            descriptions.append(f"{rule['label']} ({rule['mapping'][dataset]}): {rule['value']}")
    for rule in local_filters:
        if filter_is_active(rule):
            descriptions.append(f"lokal {rule['column']}: {rule['value']}")
    return '; '.join(descriptions) or 'Seluruh record valid; tanpa filter aktif'
