import pandas as pd
import pytest
from studio.aggregation import count_pivot, calculate, IndicatorError
from studio.aggregation import calculate_pivot, scalar, compute_component
from studio.config import new_component, new_design, export_design, import_design, DesignError
from studio.rendering import build_pivot_figure
from studio.presentation import apply_visual_defaults


def test_pivot_matches_population_indicator_and_leaves_source_unchanged(bundle):
    source = bundle.frame('penduduk')
    before = source.copy(deep=True)
    table = count_pivot(source, 'dusun', 'jenis_kelamin')
    assert table.loc['Dusun I'].to_dict() == {'Laki-laki': 123, 'Perempuan': 81, 'Total': 204}
    assert table.loc['Total'].to_dict() == {'Laki-laki': 610, 'Perempuan': 409, 'Total': 1019}
    indicator = calculate(source, {'method': 'count'}, 'dusun')
    assert table.loc['Total', 'Total'] == indicator.total
    assert table.loc[table.index != 'Total', 'Total'].tolist() == indicator.table.Nilai.tolist()
    pd.testing.assert_frame_equal(source, before)


def test_pivot_keeps_missing_categories_and_handles_total_label_collision():
    frame = pd.DataFrame({'a': ['A', 'A', None, 'Total'], 'b': ['X', None, 'Y', 'X']})
    table = count_pivot(frame, 'a', 'b')
    assert table.loc['(Kosong)', 'Y'] == 1
    assert table.loc['A', '(Kosong)'] == 1
    assert table.loc['A', 'Y'] == 0
    assert table.loc['Total', 'X'] == 1
    assert table.loc['Total keseluruhan', 'Total keseluruhan'] == 4
    assert count_pivot(frame.iloc[:0], 'a', 'b').empty


@pytest.mark.parametrize('rows,columns,message', [
    ('dusun', 'dusun', 'berbeda'),
    ('dusun', 'nik', 'Identitas pribadi'),
    ('dusun', 'hilang', 'tidak tersedia'),
])
def test_pivot_rejects_invalid_or_private_dimensions(bundle, rows, columns, message):
    with pytest.raises(IndicatorError, match=message):
        count_pivot(bundle.frame('penduduk'), rows, columns)


def population_pivot(visual='bar'):
    return new_component('penduduk','pivot','Penduduk per dusun dan jenis kelamin',dimension='dusun',unit='jiwa',
                         pivot={'column':'jenis_kelamin','granularity':'category','visualization':visual})


@pytest.mark.parametrize('method',['count','count_filled','nunique','sum','mean','median','min','max','percentage'])
def test_pivot_cells_and_margins_share_the_indicator_engine(method):
    frame=pd.DataFrame({'a':['A','A','A','B','B'], 'b':['X','X','Y','X','X'],
                        'nilai':pd.Series([10,20,50,20,None],dtype='Float64'),
                        'no_kk':['KK-1','KK-1','KK-2','KK-1',None],
                        'status':['Selesai','Menunggu','Selesai','Selesai','Menunggu']})
    frame.index=[7,7,2,9,9]  # Source record indexes need not be unique.
    before=frame.copy(deep=True)
    spec={'method':method,'value_column':'no_kk' if method=='nunique' else 'nilai',
          'numerator':[{'column':'status','operator':'equals','value':'Selesai'}],'denominator':[]}
    result=calculate_pivot(frame,spec,'a','b')
    for row,column,subset in [('A','X',frame.loc[frame.a.eq('A') & frame.b.eq('X')]),
                              ('A','Total',frame.loc[frame.a.eq('A')]),
                              ('Total','X',frame.loc[frame.b.eq('X')]),
                              ('Total','Total',frame)]:
        assert result.table.loc[row,column]==pytest.approx(scalar(subset,spec))
    assert result.total==scalar(frame,spec)
    assert 'Total' not in result.cells.Baris.tolist()+result.cells.Kolom.tolist()
    pd.testing.assert_frame_equal(frame,before)


def test_pivot_dates_missing_measurements_and_zero_denominator():
    frame=pd.DataFrame({'tanggal':pd.to_datetime(['2025-01-01','2024-12-20',None]),
                        'status':['Selesai','Menunggu',None], 'nilai':pd.Series([None,None,None],dtype='Float64')})
    result=calculate_pivot(frame,{'method':'count'},'tanggal','status','month')
    assert result.table.index.tolist()==['(Kosong)','2024-12','2025-01','Total']
    assert result.table.loc['(Kosong)','(Kosong)']==1
    empty_values=calculate_pivot(frame,{'method':'sum','value_column':'nilai'},'tanggal','status','month')
    assert empty_values.total is None and empty_values.table.isna().all().all()
    percent=calculate_pivot(frame,{'method':'percentage','numerator':[],
                                  'denominator':[{'column':'status','operator':'equals','value':'Tidak ada'}]},
                            'tanggal','status','month')
    assert percent.total is None and percent.cells.Nilai.isna().all()
    assert calculate_pivot(frame.iloc[:0],{'method':'count'},'tanggal','status').rows==0


@pytest.mark.parametrize('visual',['bar','stacked','hbar','heatmap'])
def test_pivot_chart_contains_exact_cells_without_total_records(bundle,visual):
    design=new_design(bundle)
    item=population_pivot(visual)
    result=compute_component(bundle,design,item)
    figure=build_pivot_figure(result,item)
    if visual=='heatmap':
        assert figure.data[0].z.tolist()==result.table.iloc[:-1,:-1].values.tolist()
        assert 'Total' not in list(figure.data[0].x)+list(figure.data[0].y)
    else:
        values=[float(value) for trace in figure.data for value in (trace.x if visual=='hbar' else trace.y)]
        assert sum(values)==1019
        assert [trace.name for trace in figure.data]==['Laki-laki','Perempuan']
        assert [trace.marker.color for trace in figure.data][0]!=figure.data[1].marker.color


def test_pivot_json_and_storage_preserve_filters_and_both_outputs(bundle,store):
    design=new_design(bundle)
    item=population_pivot('heatmap')
    item['local_filters']=[{'column':'jenis_kelamin','kind':'category','value':['Perempuan']}]
    design['filters']=[{'id':'a'*32,'label':'Dusun','kind':'category','mapping':{'penduduk':'dusun'},'value':['Dusun I']}]
    design['components']=[item,new_component()]
    apply_visual_defaults(design)
    restored,_=import_design(export_design(design,bundle))
    assert restored==design
    assert 'pivot' not in restored['components'][1]  # Earlier component schema stays intact.
    result=compute_component(bundle,restored,restored['components'][0])
    assert result.total==result.table.loc['Total','Total']==81
    assert result.cells.Nilai.sum()==81
    group=store.create_group('Kelompok Pivot')
    store.save_result(group['token'],group['id'],restored,0)
    stored=store.get_result(group['token'],group['id'])['design']
    assert compute_component(bundle,stored,stored['components'][0]).total==81
    assert stored['components'][0]['pivot']['visualization']=='heatmap'


@pytest.mark.parametrize('changes',[
    {'column':'nik'}, {'column':'dusun'}, {'column':None}, {'visualization':'eval'},
    {'visualization':['bar']}, {'granularity':'week'}, {'records':[]},
])
def test_invalid_pivot_json_is_rejected(bundle,changes):
    design=new_design(bundle)
    item=population_pivot()
    item['pivot'].update(changes)
    design['components']=[item]
    with pytest.raises(DesignError):
        export_design(design,bundle)
