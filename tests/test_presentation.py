from copy import deepcopy
import json
from studio.aggregation import compute_component
from studio.config import new_design, new_component, import_design, export_design
from studio.rendering import build_figure


def test_old_design_gets_automatic_visuals_without_changing_indicators(bundle):
    original=new_design(bundle)
    original['dashboard'].update(columns=3,primary_color='#FF00FF')
    original['components']=[
        new_component('penduduk','kpi','Penduduk',row=4,position=2,span=3,color='#FF00FF'),
        new_component('pelayanan','kpi','Layanan',row=8,position=1,span=2,color='#FF00FF'),
        new_component('umkm','bar','Unit usaha',dimension='jenis_usaha',row=9,span=3,color='#FF00FF'),
    ]
    original['group_name']='Kelompok 2'
    before=[compute_component(bundle,original,item).total for item in original['components']]
    restored,_=import_design(json.dumps(original).encode())
    assert restored['group_name']==original['group_name']
    assert [item['id'] for item in restored['components']]==[item['id'] for item in original['components']]
    assert [compute_component(bundle,restored,item).total for item in restored['components']]==before
    assert restored['dashboard']['columns']==2
    assert [(c['row'],c['position'],c['span']) for c in restored['components']]==[(1,1,1),(1,2,1),(2,1,1)]
    assert len({c['color'] for c in restored['components']})==3
    reloaded,_=import_design(export_design(restored,bundle))
    assert reloaded==restored


def test_category_colors_vary_and_do_not_shift_when_filtered(bundle):
    design=new_design(bundle)
    item=new_component('penduduk','bar','Penduduk per dusun',dimension='dusun')
    full=compute_component(bundle,design,item)
    order=full.table.Kategori.tolist()
    figure=build_figure(full,item,order)
    palette=dict(zip(order,figure.data[0].marker.color))
    assert len(set(palette.values()))>1
    filtered_item=deepcopy(item)
    filtered_item['local_filters']=[{'column':'dusun','kind':'category','value':['Dusun II','Dusun IV']}]
    filtered=compute_component(bundle,design,filtered_item)
    filtered_figure=build_figure(filtered,filtered_item,order)
    assert list(filtered_figure.data[0].marker.color)==[palette[c] for c in filtered.table.Kategori]
    assert list(filtered_figure.data[0].y)==filtered.table.Nilai.tolist()
