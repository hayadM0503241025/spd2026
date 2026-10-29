from datetime import date
import pandas as pd
import pytest
from studio.aggregation import scalar, calculate, compute_component, IndicatorError, format_id
from studio.config import new_component, new_design
from studio.filters import apply_filters, apply_conditions, FilterError
from studio.validation import ages_on, valid_coordinates, identity_tokens, parse_number


def test_count_filled_distinct_and_households():
    frame=pd.DataFrame({'no_kk':pd.Series(['KK-A','KK-A','KK-B',None],dtype='string')})
    assert scalar(frame,{'method':'count'})==4
    assert scalar(frame,{'method':'count_filled','value_column':'no_kk'})==3
    assert scalar(frame,{'method':'nunique','value_column':'no_kk'})==2


def test_percentage_scope_and_zero_denominator():
    frame=pd.DataFrame({'status':['Selesai','Selesai','Diproses','Menunggu'],'dusun':['A','B','A','B']})
    spec={'method':'percentage','numerator':[{'column':'status','operator':'equals','value':'Selesai'}], 'denominator':[]}
    assert scalar(frame,spec)==50
    filtered=apply_filters(frame,'pelayanan',[{'kind':'category','mapping':{'pelayanan':'dusun'},'value':['A']}])
    assert scalar(filtered,spec)==50
    spec['denominator']=[{'column':'dusun','operator':'equals','value':'A'}]
    assert scalar(frame,spec)==50  # Numerator must also be restricted to dusun A.
    spec['denominator']=[{'column':'dusun','operator':'equals','value':'C'}]
    assert scalar(frame,spec) is None
    assert format_id(None)=='Tidak tersedia'


def test_missing_measurements_are_not_zero():
    frame=pd.DataFrame({'value':pd.Series([None,None],dtype='Float64')})
    for method in ('sum','mean','median','min','max'):
        assert scalar(frame,{'method':method,'value_column':'value'}) is None


def test_non_measurements_cannot_be_summed():
    for column in ('nik','no_kk','ID','keterangan','latitude'):
        with pytest.raises(IndicatorError):
            scalar(pd.DataFrame({column:[10,20]}),{'method':'sum','value_column':column})


def test_explicit_mapping_and_local_filter_never_mutate_source():
    source=pd.DataFrame({'dusun':['A','B'],'alamat':['A','B'],'usia':[20,40], 'tanggal':pd.to_datetime(['2025-01-01','2025-02-01'])})
    original=source.copy(deep=True)
    rule={'kind':'category','mapping':{'penduduk':'dusun','pelayanan':'dusun'},'value':['A']}
    assert len(apply_filters(source,'penduduk',[rule]))==1
    assert len(apply_filters(source,'umkm',[rule]))==2
    explicit={'kind':'category','mapping':{'umkm':'alamat'},'value':['A']}
    assert len(apply_filters(source,'umkm',[explicit]))==1
    assert len(apply_filters(source,'penduduk',[],[{'kind':'number','column':'usia','value':[25,50]}]))==1
    assert len(apply_filters(source,'pelayanan',[],[{'kind':'date','column':'tanggal','value':['2025-01-01','2025-01-31']}]))==1
    pd.testing.assert_frame_equal(source,original)


def test_service_date_filter_does_not_filter_birth_date():
    rule={'kind':'date','mapping':{'pelayanan':'tanggal'},'value':['2025-01-01','2025-12-31']}
    residents=pd.DataFrame({'tanggal_lahir':pd.to_datetime(['1990-01-01'])})
    assert len(apply_filters(residents,'penduduk',[rule]))==1


def test_chronological_months_and_missing_values():
    frame=pd.DataFrame({'tanggal':pd.to_datetime(['2025-02-01','2024-12-10','2025-01-01','2024-12-15'])})
    result=calculate(frame,{'method':'count'},'tanggal','month')
    assert result.table.Kategori.tolist()==['2024-12','2025-01','2025-02']
    assert result.table.Nilai.tolist()==[2,1,1]
    assert result.total==4


def test_age_reference_birthday_future_and_missing():
    dates=pd.Series(['2000-10-29','2000-10-30','2027-01-01',None])
    ages=ages_on(dates,date(2026,10,29))
    assert ages.iloc[:2].tolist()==[26,25]
    assert ages.iloc[2:].isna().all()


def test_coordinates_never_rescaled():
    frame=pd.DataFrame({'latitude':[-6.5,-65628,91,None,-90],'longitude':[106.7,1067210,10,10,180]})
    assert valid_coordinates(frame).tolist()==[True,False,False,False,True]
    assert frame.latitude.iloc[1]==-65628


def test_invalid_excel_identity_not_reconstructed():
    values=pd.Series(['1234567890123456','1234567890123456',1234567890123456.0,None,'abc'])
    output,invalid=identity_tokens(values,'KK')
    assert output.nunique()==1
    assert output.iloc[0]==output.iloc[1]
    assert output.iloc[2:].isna().all()
    assert invalid==2


def test_indonesian_number_formats():
    assert parse_number('Rp 5.000.000')==5000000
    assert parse_number('1.250,50')==1250.5
    assert parse_number(1250.5)==1250.5
    assert format_id(1250,0,'jiwa')=='1.250 jiwa'
    assert format_id(49.6,1,'%')=='49,6%'


def test_missing_column_and_empty_result():
    with pytest.raises(IndicatorError,match='tidak tersedia'):
        scalar(pd.DataFrame({'x':[1]}),{'method':'mean','value_column':'hilang'})
    with pytest.raises(FilterError,match='hilang'):
        apply_filters(pd.DataFrame({'x':[1]}),'a',[],[{'kind':'category','column':'hilang','value':['A']}])
    result=calculate(pd.DataFrame({'x':pd.Series([],dtype='string')}),{'method':'count'},'x')
    assert result.rows==0 and result.unavailable=='Tidak ada data sesuai filter.'


def test_same_indicator_filter_different_visualization(bundle):
    design=new_design(bundle)
    design['filters']=[{'id':'a'*32,'label':'Dusun','kind':'category','mapping':{'pelayanan':'dusun'},'value':['Dusun I']}]
    item=new_component('pelayanan','kpi','Selesai',method='percentage',numerator=[{'column':'status','operator':'equals','value':'Selesai'}])
    results=[]
    for kind in ('kpi','bar','hbar','line','table'):
        item['kind']=kind
        item['dimension']='tanggal' if kind=='line' else 'status'
        item['granularity']='month' if kind=='line' else 'category'
        results.append(compute_component(bundle,design,item).total)
    assert len(set(results))==1


def test_household_tokens_and_baseline_counts(bundle):
    assert {k:len(bundle.frame(k)) for k in bundle.ids}=={'penduduk':1019,'pelayanan':20,'umkm':15,'potensi':8}
    frame=bundle.frame('penduduk')
    assert 'nama' not in frame and 'tanggal_lahir' not in frame
    assert frame.nik.dropna().str.startswith('NIK-').all()
    assert frame.no_kk.dropna().str.startswith('KK-').all()
    assert frame.no_kk.isna().sum()==19
    for dataset in ('umkm','potensi'):
        assert bundle.frame(dataset)[['latitude','longitude']].isna().all().all()


def test_readonly_bundle_returns_independent_copies(bundle):
    frame=bundle.frame('penduduk')
    frame.loc[:,'dusun']='DIUBAH'
    assert 'DIUBAH' not in bundle.frame('penduduk').dusun.tolist()
    metadata=bundle.manifest
    metadata['processing']['age_reference']='2099-01-01'
    assert bundle.manifest['processing']['age_reference']=='2026-10-29'
