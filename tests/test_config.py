from copy import deepcopy
import json
import pytest
from studio.config import (new_design, example_design, new_component, export_design,
                           import_design, validate_design, DesignError, duplicate_component, move_component, ordered_components)
from studio.data import DatasetError


def test_roundtrip_all_design_state(bundle):
    original=example_design(bundle)
    original['group_name']='Kelompok Padi'
    original['filters'][0]['value']=['Dusun II']
    restored,matched=import_design(export_design(original,bundle))
    assert restored==original and matched.version==bundle.version
    restored['filters'][0]['value'].append('Dusun IV')
    assert original['filters'][0]['value']==['Dusun II']
    payload=export_design(original,bundle).decode('utf-8')
    assert 'records' not in payload and 'tanggal_lahir' not in payload


@pytest.mark.parametrize('payload',[b'not json',b'[]',b'{"a":1,"a":2}',b'{"x":NaN}',b'\xff',b'x'*(2*1024*1024+1)],ids=['invalid','array','duplicates','nan','encoding','oversized'])
def test_bad_json_is_rejected(payload):
    with pytest.raises(DesignError):
        import_design(payload)


def test_incompatible_dataset_and_processing_rejected(bundle):
    original=example_design(bundle)
    unknown=deepcopy(original)
    unknown['dataset_ref']['version']='unavailable'
    with pytest.raises(DatasetError,match='belum dipasang'):
        import_design(json.dumps(unknown).encode())
    for section,key in [('processing','age_reference'),('dataset_ref','source_sha256')]:
        changed=deepcopy(original)
        changed[section][key]='different'
        with pytest.raises(DesignError):
            validate_design(changed,bundle)


def test_unknown_keys_duplicate_ids_and_invalid_color_rejected(bundle):
    original=example_design(bundle)
    mutations=[lambda d:d.update(raw_records=[]),
               lambda d:d['components'].append(deepcopy(d['components'][0])),
               lambda d:d['components'][0].update(color='red; script'),
               lambda d:d['components'][0].update(method='eval'),
               lambda d:d['components'][0].update(dimension='nik'),
               lambda d:d['components'][0].update(kind=['bar']),
               lambda d:d['components'][0].update(method={'code':'sum'}),
               lambda d:d['components'][0].update(kind='pie',method='mean',value_column='usia')]
    for mutate in mutations:
        candidate=deepcopy(original)
        mutate(candidate)
        with pytest.raises(DesignError):
            validate_design(candidate,bundle)


def test_missing_column_preserved_for_builder_remapping(bundle):
    from studio.aggregation import compute_component, IndicatorError
    design=new_design(bundle)
    item=new_component('penduduk','bar','Perlu dipetakan',dimension='kolom_lama')
    design['components']=[item]
    restored,_=import_design(export_design(design,bundle))
    with pytest.raises(IndicatorError,match='dimensi'):
        compute_component(bundle,restored,restored['components'][0])


def test_duplicate_edit_and_move_are_independent(bundle):
    design=example_design(bundle,'Kependudukan')
    first=design['components'][0]
    cloned=duplicate_component(design,first['id'])
    assert cloned['id']!=first['id']
    cloned['local_filters'].append({'column':'dusun','kind':'category','value':['Dusun I']})
    assert first['local_filters']==[]
    move_component(design,first['id'],1)
    assert ordered_components(design)[1]['id']==first['id']


def test_baseline_file_integrity_checked(bundle,tmp_path,monkeypatch):
    import studio.data as data
    version=bundle.version
    folder=tmp_path/'data'/'shared'/version
    folder.mkdir(parents=True)
    (folder/'manifest.json').write_text(bundle.metadata_json,encoding='utf-8')
    for dataset,payload in bundle.payloads:
        (folder/f'{dataset}.csv').write_bytes(payload)
    (tmp_path/'data'/'registry.json').write_text(json.dumps({'current':version,'versions':{version:version}}),encoding='utf-8')
    monkeypatch.setattr(data,'ROOT',tmp_path)
    assert data.load_shared().version==version
    (folder/'penduduk.csv').write_bytes(b'changed')
    with pytest.raises(DatasetError,match='Integritas'):
        data.load_shared()


def legacy_starter(bundle):
    design=example_design(bundle)
    design['dashboard'].update(village='Desa Maju',title='Desa dalam angka',description='Membaca kondisi desa, merancang langkah bersama.')
    design['group_name']='Kelompok yang sudah diberi nama'
    return design


def test_untouched_old_starter_is_retired_but_group_name_kept(bundle):
    from studio.config import retire_untouched_example
    design=legacy_starter(bundle)
    migrated=retire_untouched_example(design,bundle)
    assert migrated['components']==[] and migrated['filters']==[]
    assert migrated['group_name']==design['group_name']
    assert design['components']  # The input is not mutated.


def test_customized_old_work_is_never_auto_cleared(bundle):
    from studio.config import retire_untouched_example
    for mutate in (lambda d:d['components'][0].update(title='Hasil kelompok'),
                   lambda d:d['filters'][0].update(value=['Dusun I']),
                   lambda d:d['dashboard'].update(title='Dashboard kami')):
        design=legacy_starter(bundle)
        mutate(design)
        assert retire_untouched_example(design,bundle) is None
