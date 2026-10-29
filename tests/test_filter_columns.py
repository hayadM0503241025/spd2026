from studio.filters import filter_columns, select_filter_columns
from studio.config import uid


def test_column_choices_explain_scope_and_infer_types(bundle):
    options=filter_columns(bundle)
    assert options['dusun:category']['mapping']=={'penduduk':'dusun','pelayanan':'dusun'}
    assert options['alamat:category']['mapping']=={'umkm':'alamat','potensi':'alamat'}
    assert options['tanggal:date']['mapping']=={'pelayanan':'tanggal'}
    assert options['usia:number']['mapping']=={'penduduk':'usia'}
    assert not any(key.startswith(('nik:','no_kk:','nama:','ID:','latitude:','longitude:')) for key in options)


def test_select_columns_includes_all_data_and_preserves_existing_values(bundle):
    options=filter_columns(bundle)
    rules=select_filter_columns([],['dusun:category','usia:number','tanggal:date'],options,uid)
    assert [r['value'] for r in rules]==[[],None,None]
    rules[0]['value']=['Dusun II']
    kept=select_filter_columns(rules,['dusun:category','usia:number'],options,uid)
    assert kept[0]['id']==rules[0]['id'] and kept[0]['value']==['Dusun II']
    kept[0]['value'].append('Dusun I')
    kept[0]['mapping']['potensi']='alamat'
    assert rules[0]['value']==['Dusun II'] and 'potensi' not in rules[0]['mapping']
    assert select_filter_columns(rules,[],options,uid)==[]


def test_imported_custom_mapping_remains_selectable_without_changes(bundle):
    original={'id':uid(),'label':'Hanya penduduk A','kind':'category','mapping':{'penduduk':'dusun'},'value':['Dusun I']}
    options=filter_columns(bundle,[original])
    selected='saved:'+original['id']
    assert options[selected]['mapping']=={'penduduk':'dusun'}
    assert select_filter_columns([original],[selected],options,uid)==[original]
