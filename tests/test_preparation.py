from datetime import date, datetime
from tools.prepare_shared import prepare_sheet


def test_formula_only_rows_and_extra_unnamed_cells():
    rows=[('ID','nik','nama','jenis_kelamin','tanggal_lahir','usia','kelompok_usia','pendidikan','pekerjaan','dusun','no_kk'),
          (1,'1234567890123456','Nama rahasia','Perempuan',datetime(2000,1,1),'=DATEDIF()','=IF()','SMA','Petani','A','2345678901234567','extraneous formatting'),
          (None,None,None,None,None,'=DATEDIF()','=IF()',None,None,None,None),
          (None,)*11]
    frame,reports,removed=prepare_sheet(rows,'penduduk',date(2026,10,29))
    assert len(frame)==1 and removed==2
    assert frame.usia.iloc[0]==26
    assert frame.kelompok_usia.iloc[0]=='15–59 tahun'
    assert 'nama' not in frame and 'tanggal_lahir' not in frame
    assert not any('Nama rahasia' in r['message'] for r in reports)
