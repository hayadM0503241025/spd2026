from copy import deepcopy
import pytest
from test_app import start, healthy, goto, select, text
from studio.aggregation import compute_component
from studio.config import import_design, export_design
from studio.data import load_shared


def open_pivot(app):
    goto(app,'Rancang Dashboard')
    app.button(key='add_pivot').click().run()
    healthy(app)
    assert app.radio(key='stage').value=='Tambah Pivot'


@pytest.mark.parametrize('dataset,rows,columns,expected',[
    ('penduduk','dusun','jenis_kelamin',1019),
    ('pelayanan','jenis_layanan','status',20),
    ('umkm','alamat','jenis_usaha',15),
    ('potensi','kategori','kondisi',8),
])
def test_choose_dataset_axes_then_visual_and_add_table_with_chart(dataset,rows,columns,expected):
    app=start()
    open_pivot(app)
    assert not any(widget.label=='Visualisasi pivot' for widget in app.selectbox)
    assert not any(widget.key=='save_pivot' for widget in app.button)
    select(app,'Dataset sumber pivot',dataset)
    select(app,'Baris pivot',rows)
    select(app,'Kolom pivot',columns)
    assert not app.session_state['design']['components']
    app.button(key='show_pivot').click().run()
    healthy(app)
    assert app.dataframe[0].value.loc['Total','Total']==expected
    select(app,'Visualisasi pivot','heatmap')
    app.button(key='save_pivot').click().run()
    healthy(app)
    assert app.radio(key='stage').value=='Pratinjau'
    item=deepcopy(app.session_state['design']['components'][0])
    assert item['kind']=='pivot' and item['pivot']['visualization']=='heatmap'
    assert item['dataset']==dataset and item['dimension']==rows and item['pivot']['column']==columns
    goto(app,'Pratinjau')
    assert len(app.dataframe)==len(app.get('plotly_chart'))==1
    assert app.dataframe[0].value.loc['Total','Total']==expected
    app.button(key='open_presentation').click().run()
    healthy(app)
    assert len(app.dataframe)==len(app.get('plotly_chart'))==1


def test_pivot_edit_duplicate_json_and_filters_are_isolated_between_sessions():
    a,b=start(),start()
    for app in (a,b):
        open_pivot(app)
        app.button(key='show_pivot').click().run()
        healthy(app)
        app.button(key='save_pivot').click().run()
        healthy(app)
    untouched_b=deepcopy(b.session_state['design'])
    item=deepcopy(a.session_state['design']['components'][0])
    goto(a,'Rancang Dashboard')
    a.button(key='edit_'+item['id']).click().run()
    healthy(a)
    assert a.radio(key='stage').value=='Tambah Pivot'
    select(a,'Visualisasi pivot','hbar')
    local=next(widget for widget in a.multiselect if widget.label=='Kolom filter khusus komponen')
    local.set_value(['dusun']).run()
    healthy(a)
    value=next(widget for widget in a.multiselect if widget.label=='dusun')
    assert value.options==['Dusun I','Dusun II','Dusun III','Dusun IV','Dusun V']
    value.set_value(['Dusun I']).run()
    healthy(a)
    assert a.dataframe[0].value.loc['Total','Total']==204
    goto(a,'Panduan')
    goto(a,'Tambah Pivot')
    assert a.dataframe[0].value.loc['Total','Total']==204
    assert next(widget for widget in a.selectbox if widget.label=='Visualisasi pivot').value=='hbar'
    select(a,'Baris pivot','pendidikan')
    assert not any(widget.key=='save_pivot' for widget in a.button)  # Axes changed: inspect the new table first.
    a.button(key='show_pivot').click().run()
    a.button(key='save_pivot').click().run()
    healthy(a)
    assert len(a.session_state['design']['components'])==1
    assert a.session_state['design']['components'][0]['id']==item['id']
    goto(a,'Rancang Dashboard')
    a.button(key='duplicate_'+item['id']).click().run()
    healthy(a)
    cloned=deepcopy(a.session_state['design']['components'][1])
    a.button(key='edit_'+cloned['id']).click().run()
    select(a,'Visualisasi pivot','heatmap')
    a.button(key='save_pivot').click().run()
    healthy(a)
    design=a.session_state['design']
    assert design['components'][0]['pivot']['visualization']=='hbar'
    assert design['components'][1]['pivot']['visualization']=='heatmap'
    restored,bundle=import_design(export_design(design,load_shared()))
    assert restored==design
    assert [compute_component(bundle,restored,value).total for value in restored['components']]==[204,204]
    assert b.session_state['design']==untouched_b
    goto(a,'Pratinjau')
    goto(b,'Pratinjau')
    assert len(a.dataframe)==len(a.get('plotly_chart'))==2
    assert a.dataframe[0].value.loc['Total','Total']==204
    assert b.dataframe[0].value.loc['Total','Total']==1019
    goto(b,'Rancang Dashboard')
    second_id=b.session_state['design']['components'][0]['id']
    b.button(key='edit_'+second_id).click().run()
    local=next(widget for widget in b.multiselect if widget.label=='Kolom filter khusus komponen')
    local.set_value(['dusun']).run()
    next(widget for widget in b.multiselect if widget.label=='dusun').set_value(['Dusun I']).run()
    b.button(key='save_pivot').click().run()
    healthy(b)
    # Same count and filter in both groups: totals match despite different charts.
    assert b.dataframe[0].value.loc['Total','Total']==a.dataframe[0].value.loc['Total','Total']==204


def test_pivot_draft_preserves_regular_draft_and_workspace_reset_needs_confirmation():
    app=start()
    goto(app,'Rancang Dashboard')
    text(app,'Judul komponen','Draft komponen biasa')
    regular=deepcopy(app.session_state['component_draft'])
    app.button(key='add_pivot').click().run()
    text(app,'Judul pivot','Draft pivot')
    goto(app,'Beranda')
    app.button(key='clear_session').click().run()
    healthy(app)
    assert app.session_state['pivot_draft']['title']=='Draft pivot'
    assert app.session_state['component_draft']==regular
    app.button(key='cancel_workspace_action').click().run()
    goto(app,'Tambah Pivot')
    assert next(widget for widget in app.text_input if widget.label=='Judul pivot').value=='Draft pivot'
    app.button(key='show_pivot').click().run()
    app.button(key='save_pivot').click().run()
    healthy(app)
    goto(app,'Rancang Dashboard')
    assert app.session_state['component_draft']['title']=='Draft komponen biasa'
    assert app.session_state['design']['components'][0]['title']=='Draft pivot'
    app.button(key='clear_session').click().run()
    app.button(key='confirm_workspace_action').click().run()
    healthy(app)
    assert 'pivot_draft' not in app.session_state
    assert app.session_state['design']['components']==[]


def test_numeric_pivot_and_date_grouping_use_source_values():
    app=start()
    open_pivot(app)
    select(app,'Dataset sumber pivot','pelayanan')
    select(app,'Baris pivot','tanggal')
    select(app,'Kolom pivot','status')
    select(app,'Metode perhitungan pivot','mean')
    select(app,'Kolom nilai pivot','lama_proses')
    app.button(key='show_pivot').click().run()
    healthy(app)
    assert '2025-01' in app.dataframe[0].value.index
    frame=load_shared().frame('pelayanan')
    assert app.dataframe[0].value.loc['Total','Total']==pytest.approx(frame.lama_proses.mean())
    assert 'Batang bertumpuk' not in next(widget for widget in app.selectbox if widget.label=='Visualisasi pivot').options
