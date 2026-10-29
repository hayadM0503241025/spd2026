"""Create small, clearly synthetic CSV learning files, unrelated to the baseline."""
from pathlib import Path
import csv

root=Path(__file__).resolve().parents[1]/'data'/'examples'
root.mkdir(parents=True,exist_ok=True)
tables={
    'penduduk':[
        {'ID':i,'nik':f'SIM-NIK-{i:03d}','jenis_kelamin':'Perempuan' if i%2 else 'Laki-laki',
         'usia':18+i*3,'kelompok_usia':'15–59 tahun','pendidikan':['SMA','SMP','S1'][i%3],
         'pekerjaan':['Petani','Pedagang','Pelajar'][i%3],'dusun':['Dusun Contoh A','Dusun Contoh B'][i%2],
         'no_kk':f'SIM-KK-{(i+1)//2:03d}'} for i in range(1,13)],
    'pelayanan':[
        {'ID':i,'tanggal':f'{2024 if i<3 else 2025}-{12 if i<3 else (i-3)//2+1:02d}-10',
         'jenis_layanan':['Surat keterangan','Surat pengantar'][i%2],
         'dusun':['Dusun Contoh A','Dusun Contoh B'][i%2],
         'status':['Selesai','Selesai','Diproses','Menunggu'][i%4],'lama_proses':(i%5)+1} for i in range(1,13)],
    'umkm':[
        {'ID':i,'nama_umkm':f'Usaha Simulasi {i}','alamat':f'Dusun Contoh {"A" if i%2 else "B"}',
         'latitude':-6.5-i*.001,'longitude':106.7+i*.001,'jenis_usaha':['Kuliner','Kerajinan','Jasa'][i%3],
         'produk':f'Produk simulasi {i}','omset':i*1000000} for i in range(1,7)],
    'potensi':[
        {'ID':i,'potensi':f'Objek Simulasi {i}','alamat':f'Dusun Contoh {"A" if i%2 else "B"}',
         'latitude':-6.5-i*.001,'longitude':106.7+i*.001,'kategori':['Pertanian','Wisata'][i%2],
         'kondisi':'Berkembang','keterangan':'Contoh sintetis; bukan hasil survei'} for i in range(1,5)],
}
for name,rows in tables.items():
    with (root/f'{name}.csv').open('w',encoding='utf-8',newline='') as output:
        writer=csv.DictWriter(output,fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
print('4 CSV simulasi dibuat.')
