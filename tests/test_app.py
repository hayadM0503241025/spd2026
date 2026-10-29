"""Real Streamlit script sessions via AppTest, not browser rendering tests."""
from copy import deepcopy
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from studio.config import export_design, import_design
from studio.data import load_shared

APP=Path(__file__).resolve().parents[1]/'app.py'


def start():
    app=AppTest.from_file(str(APP),default_timeout=30).run()
    healthy(app)
    return app


def healthy(app):
    assert not app.exception, [x.message for x in app.exception]
    assert not any('Komponen perlu diperiksa' in x.value for x in app.warning)


def select(app,label,value):
    widget=next(x for x in app.selectbox if x.label==label)
    widget.select(value).run()
    healthy(app)


def text(app,label,value):
    widget=next(x for x in app.text_input if x.label==label)
    widget.set_value(value).run()
    healthy(app)


def goto(app,stage):
    app.radio(key='stage').set_value(stage).run()
    healthy(app)


def add_population_components(app):
    goto(app,'Rancang Dashboard')
    text(app,'Judul komponen','Jumlah penduduk')
    text(app,'Satuan (jiwa, layanan, unit, Rp, %)','jiwa')
    app.button(key='save_component').click().run()
    healthy(app)
    text(app,'Judul komponen','Penduduk per dusun')
    select(app,'Jenis komponen','hbar')
    select(app,'Kolom kategori / dimensi','dusun')
    app.button(key='save_component').click().run()
    healthy(app)
    app.multiselect(key='w_dashboard_filter_columns').set_value(['dusun:category']).run()
    healthy(app)


def test_builder_add_edit_duplicate_reorder_delete_and_presentation():
    app=start()
    app.button(key='start_blank').click().run()
    healthy(app)
    assert app.radio(key='stage').value=='Rancang Dashboard'
    assert app.session_state['design']['components']==[]
    assert not app.get('color_picker')
    assert 'Warna & posisi' not in [e.label for e in app.expander]
    assert not {'Baris','Urutan dalam baris','Lebar (jumlah kolom)','Jumlah kolom per baris'} & {e.label for e in list(app.selectbox)+list(app.number_input)}
    text(app,'Judul komponen','Penduduk per dusun')
    select(app,'Jenis komponen','bar')
    select(app,'Kolom kategori / dimensi','dusun')
    app.button(key='save_component').click().run()
    healthy(app)
    first=deepcopy(app.session_state['design']['components'][0])
    assert first['kind']=='bar' and first['dimension']=='dusun'
    app.button(key='duplicate_'+first['id']).click().run()
    healthy(app)
    cloned=deepcopy(app.session_state['design']['components'][1])
    assert cloned['id']!=first['id']
    app.button(key='edit_'+cloned['id']).click().run()
    select(app,'Jenis komponen','donut')
    text(app,'Judul komponen','Versi donut')
    app.button(key='save_component').click().run()
    healthy(app)
    originals=app.session_state['design']['components']
    assert originals[0]['kind']=='bar' and originals[0]['title']=='Penduduk per dusun'
    assert originals[1]['kind']=='donut'
    app.button(key='up_'+cloned['id']).click().run()
    healthy(app)
    from studio.config import ordered_components
    assert ordered_components(app.session_state['design'])[0]['id']==cloned['id']
    app.button(key='delete_'+first['id']).click().run()
    healthy(app)
    assert len(app.session_state['design']['components'])==1
    goto(app,'Pratinjau')
    app.button(key='open_presentation').click().run()
    healthy(app)
    assert app.session_state['presentation'] is True
    assert not app.text_input and not app.selectbox
    assert len(app.get('plotly_chart'))==1
    next(x for x in app.button if x.label=='Kembali ke Mode Rancang').click().run()
    healthy(app)
    assert app.radio(key='stage').value=='Rancang Dashboard'


def test_two_independent_sessions_same_baseline_different_designs_and_filters():
    a,b=start(),start()
    text(a,'Nama kelompok','Kelompok A')
    text(b,'Nama kelompok','Kelompok B')
    add_population_components(a)
    add_population_components(b)
    assert a.session_state['design']['dataset_ref']==b.session_state['design']['dataset_ref']
    assert a.session_state['design']['processing']==b.session_state['design']['processing']
    assert a.session_state['design']['components'][0]['id']!=b.session_state['design']['components'][0]['id']
    goto(a,'Pratinjau')
    goto(b,'Pratinjau')
    assert a.metric[0].value==b.metric[0].value=='1.019 jiwa'
    filter_a=a.multiselect[0].key
    a.multiselect(key=filter_a).set_value(['Dusun I']).run()
    healthy(a)
    b.run()
    healthy(b)
    assert a.metric[0].value=='204 jiwa'
    assert b.metric[0].value=='1.019 jiwa'
    assert b.session_state['design']['filters'][0]['value']==[]
    goto(a,'Rancang Dashboard')
    original_id=a.session_state['design']['components'][1]['id']
    a.button(key='edit_'+original_id).click().run()
    select(a,'Jenis komponen','bar')
    text(a,'Judul komponen','Grafik kelompok A')
    a.button(key='save_component').click().run()
    healthy(a)
    assert b.session_state['design']['components'][1]['kind']=='hbar'
    assert b.session_state['design']['components'][1]['title']!='Grafik kelompok A'
    # Matching filter + indicator + calculation => identical numeric results.
    b.multiselect[0].set_value(['Dusun I']).run()
    healthy(b)
    goto(a,'Pratinjau')
    assert [(m.label,m.value) for m in a.metric]==[(m.label,m.value) for m in b.metric]
    from studio.aggregation import compute_component
    baseline=load_shared()
    da,db=a.session_state['design'],b.session_state['design']
    assert compute_component(baseline,da,da['components'][1]).total==compute_component(baseline,db,db['components'][1]).total
    # Same group label still does not share mutable state.
    text(b,'Nama kelompok','Kelompok A')
    a.button(key='reset_filters').click().run()
    healthy(a)
    b.run()
    assert b.session_state['design']['filters'][0]['value']==['Dusun I']
    assert b.metric[0].value=='204 jiwa'
    saved,_=import_design(export_design(b.session_state['design'],baseline))
    assert saved['group_name']=='Kelompok A' and saved['filters'][0]['value']==['Dusun I']
    a.button(key='clear_session').click().run()
    healthy(a)
    assert a.session_state['design']['components']  # Destructive actions require confirmation.
    a.button(key='confirm_workspace_action').click().run()
    healthy(a)
    assert a.session_state['design']['components']==[]
    assert b.session_state['design']['group_name']=='Kelompok A'


@pytest.mark.parametrize('example',['Kependudukan','Pelayanan','Ekonomi desa'])
def test_examples_inspection_save_and_guidance_pages(example):
    app=start()
    before=deepcopy(app.session_state['design'])
    app.button(key='example_'+example).click().run()
    healthy(app)
    assert app.radio(key='stage').value=='Beranda'
    assert app.get('plotly_chart')
    assert app.session_state['design']==before
    for page in ('Periksa Data','Pratinjau','Simpan & Muat','Panduan'):
        goto(app,page)
        if page=='Pratinjau':
            assert not app.get('plotly_chart') and not app.metric
            assert not app.session_state['design']['components']
    assert len(app.get('download_button'))==4


def test_draft_survives_navigation_and_filter_mapping_can_be_added_removed():
    app=start()
    app.button(key='start_blank').click().run()
    text(app,'Judul komponen','Draft belum disimpan')
    select(app,'Jenis komponen','hbar')
    select(app,'Kolom kategori / dimensi','pendidikan')
    goto(app,'Periksa Data')
    goto(app,'Rancang Dashboard')
    assert next(x for x in app.text_input if x.label=='Judul komponen').value=='Draft belum disimpan'
    assert next(x for x in app.selectbox if x.label=='Jenis komponen').value=='hbar'
    assert next(x for x in app.selectbox if x.label=='Kolom kategori / dimensi').value=='pendidikan'
    app.multiselect(key='w_dashboard_filter_columns').set_value(['dusun:category']).run()
    healthy(app)
    rules=app.session_state['design']['filters']
    assert len(rules)==1
    assert rules[0]['mapping']=={'penduduk':'dusun','pelayanan':'dusun'}
    assert rules[0]['value']==[]
    assert not any(x.key.startswith('w_filter_') for x in app.multiselect)
    app.multiselect(key='w_dashboard_filter_columns').set_value([]).run()
    healthy(app)
    assert app.session_state['design']['filters']==[]


def test_empty_preview_and_examples_never_replace_group_work():
    app=start()
    assert app.session_state['design']['components']==[]
    goto(app,'Pratinjau')
    assert not app.metric and not app.get('plotly_chart') and not app.multiselect
    goto(app,'Rancang Dashboard')
    assert not app.metric and not app.get('plotly_chart')
    text(app,'Judul komponen','Angka kelompok sendiri')
    app.button(key='save_component').click().run()
    healthy(app)
    before=deepcopy(app.session_state['design'])
    goto(app,'Beranda')
    app.button(key='example_Pelayanan').click().run()
    healthy(app)
    assert app.session_state['design']==before
    goto(app,'Pratinjau')
    assert [m.label for m in app.metric]==['Angka kelompok sendiri']
    assert not app.get('plotly_chart')


def test_filter_column_exposes_every_value_only_in_preview():
    app=start()
    add_population_components(app)
    rules=app.session_state['design']['filters']
    assert len(rules)==1 and rules[0]['value']==[]
    assert not any(x.key.startswith('w_filter_') for x in app.multiselect)
    assert not app.metric  # The component draft preview is opt-in.
    goto(app,'Pratinjau')
    expected=['Dusun I','Dusun II','Dusun III','Dusun IV','Dusun V']
    assert app.multiselect[0].options==expected
    assert app.multiselect[0].value==[]
    assert app.metric[0].value=='1.019 jiwa'
    app.multiselect[0].set_value(['Dusun I']).run()
    healthy(app)
    assert app.multiselect[0].options==expected  # Choices always come from the full source column.
    assert app.metric[0].value=='204 jiwa'
    goto(app,'Rancang Dashboard')
    assert app.session_state['design']['filters'][0]['value']==['Dusun I']
    goto(app,'Pratinjau')
    assert app.metric[0].value=='204 jiwa'
    app.button(key='reset_filters').click().run()
    healthy(app)
    assert app.metric[0].value=='1.019 jiwa'


def test_local_filter_column_is_used_in_preview_and_is_saved():
    app=start()
    goto(app,'Rancang Dashboard')
    text(app,'Judul komponen','Penduduk dengan filter lokal')
    text(app,'Satuan (jiwa, layanan, unit, Rp, %)','jiwa')
    local=next(x for x in app.multiselect if x.label=='Kolom filter khusus komponen')
    local.set_value(['jenis_kelamin']).run()
    healthy(app)
    assert not any(x.label=='jenis_kelamin' for x in app.multiselect)
    app.button(key='save_component').click().run()
    healthy(app)
    goto(app,'Pratinjau')
    assert app.multiselect[0].options==['Laki-laki','Perempuan']
    assert app.metric[0].value=='1.019 jiwa'
    app.multiselect[0].set_value(['Perempuan']).run()
    healthy(app)
    assert app.metric[0].value=='409 jiwa'
    design=app.session_state['design']
    restored,_=import_design(export_design(design,load_shared()))
    assert restored['components'][0]['local_filters'][0]['value']==['Perempuan']
    app.button(key='open_presentation').click().run()
    healthy(app)
    assert app.multiselect[0].options==['Laki-laki','Perempuan']
    assert app.metric[0].value=='409 jiwa'


def test_number_and_date_columns_start_with_full_scope_and_can_be_narrowed():
    from datetime import date
    app=start()
    goto(app,'Rancang Dashboard')
    text(app,'Judul komponen','Jumlah penduduk')
    app.button(key='save_component').click().run()
    healthy(app)
    select(app,'Dataset sumber','pelayanan')
    text(app,'Judul komponen','Jumlah pelayanan')
    app.button(key='save_component').click().run()
    healthy(app)
    app.multiselect(key='w_dashboard_filter_columns').set_value(['usia:number','tanggal:date']).run()
    healthy(app)
    assert all(rule['value'] is None for rule in app.session_state['design']['filters'])
    assert not any(x.key.startswith('w_filter_') for x in app.checkbox) and not app.date_input
    goto(app,'Pratinjau')
    assert [m.value for m in app.metric]==['1.019','20']
    next(x for x in app.checkbox if x.label=='Batasi Usia').check().run()
    healthy(app)
    frame=load_shared().frame('penduduk')
    assert app.number_input[0].value==float(frame.usia.min())
    assert app.number_input[1].value==float(frame.usia.max())
    app.number_input[1].set_value(30.0).run()
    healthy(app)
    assert app.metric[0].value==str(int(frame.usia.le(30).sum()))
    assert app.metric[1].value=='20'
    next(x for x in app.checkbox if x.label=='Batasi Tanggal').check().run()
    healthy(app)
    app.date_input[0].set_value((date(2025,1,1),date(2025,1,31))).run()
    healthy(app)
    service=load_shared().frame('pelayanan')
    assert app.metric[1].value==str(int(service.tanggal.dt.month.eq(1).sum()))
    app.button(key='reset_filters').click().run()
    healthy(app)
    assert [m.value for m in app.metric]==['1.019','20']
    assert not any(x.value for x in app.checkbox if x.key.startswith('w_filter_'))
