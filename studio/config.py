"""Bounded, declarative JSON; no executable expressions or embedded records."""
from copy import deepcopy
import json
import math
import re
from uuid import uuid4
import pandas as pd
from studio.constants import (SCHEMA_VERSION, MAX_DESIGN_BYTES, KINDS, METHODS,
                              PRIVATE_COLUMNS, OPERATORS, NUMERIC_METHODS, PIVOT_VISUALS)
from studio.data import load_shared
from studio.aggregation import numeric_columns
from studio.presentation import apply_visual_defaults


class DesignError(ValueError):
    pass


def uid():
    return uuid4().hex


def dataset_reference(bundle):
    manifest = bundle.manifest
    return {'version': bundle.version, 'source_sha256': manifest['source_sha256'],
            'files_sha256': {k:v['sha256'] for k,v in manifest['datasets'].items()}}


def new_component(dataset='penduduk', kind='kpi', title='Indikator baru', **settings):
    item = dict(id=uid(), dataset=dataset, kind=kind, title=title, description='', question='',
                dimension=None, granularity='category', value_column=None, method='count',
                numerator=[], denominator=[], local_filters=[], color='#16715B', decimals=0,
                unit='', period='', section='', row=1, position=1, span=1, note='')
    if kind == 'pivot':
        item['pivot'] = {'column': None, 'granularity': 'category', 'visualization': 'bar'}
    item.update(settings)
    return item


def new_design(bundle):
    return {'schema_version': SCHEMA_VERSION, 'group_name': '',
            'dataset_ref': dataset_reference(bundle), 'processing': deepcopy(bundle.manifest['processing']),
            'dashboard': {'village':'Desa Anda', 'title':'Dashboard kelompok',
                          'description':'',
                          'primary_color':'#16715B', 'columns':2, 'logo':None},
            'components':[], 'filters':[]}


def example_design(bundle, example='Terpadu', identity=None):
    design = new_design(bundle)
    design['dashboard'].update(village='Desa Maju',title=f'Contoh dashboard {example.lower()}',
                               description='Contoh penyajian data bersama untuk inspirasi kelompok.')
    if identity:
        design['group_name'] = identity.get('group_name', '')
        design['dashboard'] = deepcopy(identity['dashboard'])
    def add(dataset, kind, title, **kwargs):
        if dataset not in bundle.ids:
            return
        n = len(design['components'])
        design['components'].append(new_component(dataset, kind, title, row=n//2+1, position=n%2+1, **kwargs))
    if example in ('Terpadu', 'Kependudukan'):
        add('penduduk', 'kpi', 'Jumlah penduduk', unit='jiwa')
        add('penduduk', 'kpi', 'KK unik dengan identitas valid', method='nunique', value_column='no_kk', unit='KK',
            description='Nomor KK numerik/rusak dikeluarkan; ini jumlah KK yang dapat diverifikasi, bukan estimasi seluruh KK.')
        add('penduduk', 'hbar', 'Persebaran penduduk per dusun', dimension='dusun', unit='jiwa', section='Kependudukan')
        add('penduduk', 'donut', 'Komposisi jenis kelamin', dimension='jenis_kelamin', unit='jiwa')
        if example == 'Kependudukan':
            add('penduduk', 'bar', 'Komposisi pendidikan', dimension='pendidikan', unit='jiwa')
            add('penduduk', 'bar', 'Kelompok usia', dimension='kelompok_usia', unit='jiwa')
    if example in ('Terpadu', 'Pelayanan'):
        add('pelayanan', 'kpi', 'Pelayanan selesai', method='percentage', decimals=1,
            numerator=[{'column':'status','operator':'equals','value':'Selesai'}], unit='%')
        add('pelayanan', 'line', 'Tren pelayanan bulanan', dimension='tanggal', granularity='month', unit='layanan', section='Pelayanan publik')
        if example == 'Pelayanan':
            add('pelayanan', 'kpi', 'Total pelayanan', unit='layanan')
            add('pelayanan', 'kpi', 'Rata-rata proses layanan selesai', method='mean', value_column='lama_proses', decimals=1,
                unit='', local_filters=[{'column':'status','kind':'category','value':['Selesai']}],
                description='Satuan lama_proses belum dijelaskan dalam sumber. Konfirmasikan sebelum memberi satuan hari/jam.')
            add('pelayanan', 'hbar', 'Pelayanan menurut jenis', dimension='jenis_layanan', unit='layanan')
            add('pelayanan', 'donut', 'Status pelayanan', dimension='status', unit='layanan')
    if example in ('Terpadu', 'Ekonomi desa'):
        add('umkm', 'bar', 'Unit UMKM per jenis usaha', dimension='jenis_usaha', unit='unit', section='Ekonomi desa')
        add('potensi', 'table', 'Objek potensi per kategori', dimension='kategori', unit='objek')
        if example == 'Ekonomi desa':
            add('umkm', 'kpi', 'Jumlah UMKM', unit='unit')
            add('umkm', 'hbar', 'Total omzet menurut jenis usaha', method='sum', value_column='omset', dimension='jenis_usaha', unit='Rp',
                description='Periode omzet tidak tersedia pada workbook; jangan menafsirkan sebagai omzet bulanan/tahunan.')
    mapping={d:'dusun' for d in ('penduduk','pelayanan') if d in bundle.ids}
    design['filters'] = [{'id':uid(),'label':'Dusun','kind':'category', 'mapping':mapping,'value':[]}] if mapping else []
    return apply_visual_defaults(design)


def retire_untouched_example(design,bundle):
    """Migrate only an untouched legacy starter; leave participants' work intact."""
    old_dashboard={'village':'Desa Maju','title':'Desa dalam angka',
                   'description':'Membaca kondisi desa, merancang langkah bersama.',
                   'primary_color':'#16715B','columns':2,'logo':None}
    if design['dashboard']!=old_dashboard:
        return None
    def without_ids(items):
        return [{k:v for k,v in item.items() if k!='id'} for item in items]
    for name in ('Terpadu','Kependudukan','Pelayanan','Ekonomi desa'):
        sample=example_design(bundle,name)
        if (without_ids(design['components'])==without_ids(sample['components'])
                and without_ids(design['filters'])==without_ids(sample['filters'])):
            blank=new_design(bundle)
            blank['group_name']=design['group_name']
            return blank
    return None


def require(condition, message):
    if not condition:
        raise DesignError(message)


def exact_keys(obj, keys, label):
    require(isinstance(obj, dict) and set(obj) == set(keys), f'Struktur {label} tidak sesuai skema.')


def string(value, label, maximum=300):
    require(isinstance(value, str) and len(value) <= maximum, f'{label} harus teks, maksimal {maximum} karakter.')


def integer(value, low, high, label):
    require(type(value) is int and low <= value <= high, f'{label} harus bilangan bulat {low}–{high}.')


def check_color(value):
    require(isinstance(value, str) and bool(re.fullmatch(r'#[0-9A-Fa-f]{6}', value)), 'Warna harus berformat #RRGGBB.')


def check_filter(rule, bundle, global_rule=False):
    exact_keys(rule, ('id','label','kind','mapping','value') if global_rule else ('column','kind','value'), 'filter')
    require(isinstance(rule['kind'],str) and rule['kind'] in ('category','number','date'), 'Jenis filter tidak sah.')
    if global_rule:
        require(isinstance(rule['id'],str) and bool(re.fullmatch('[a-f0-9]{32}',rule['id'])), 'ID filter tidak sah.')
        string(rule['label'], 'Label filter', 100)
        require(isinstance(rule['mapping'],dict) and 0 < len(rule['mapping']) <= len(bundle.ids), 'Pemetaan filter wajib diisi.')
        for dataset, column in rule['mapping'].items():
            require(dataset in bundle.ids, 'Dataset dalam pemetaan filter tidak tersedia.')
            string(column, 'Kolom filter', 100)
            require(column not in PRIVATE_COLUMNS, 'Filter identitas pribadi tidak diekspor dalam desain.')
    else:
        string(rule['column'], 'Kolom filter', 100)
        require(rule['column'] not in PRIVATE_COLUMNS, 'Filter identitas pribadi tidak diperbolehkan.')
    value = rule['value']
    if value is None:
        return
    if rule['kind'] == 'category':
        require(isinstance(value,list) and len(value)<=1000 and all(isinstance(x,str) and len(x)<=300 for x in value), 'Nilai filter kategori tidak sah.')
    else:
        require(isinstance(value,list) and len(value)==2, 'Rentang filter harus memiliki dua batas.')
        if rule['kind'] == 'number':
            require(all(type(x) in (int,float) and math.isfinite(x) for x in value), 'Batas filter angka harus angka terbatas.')
        else:
            require(all(isinstance(x,str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}',x)) for x in value), 'Tanggal filter harus YYYY-MM-DD.')
            try:
                [pd.Timestamp(x) for x in value]
            except (ValueError, OverflowError):
                raise DesignError('Tanggal filter tidak sah.') from None
        require(value[0] <= value[1], 'Batas awal filter melebihi batas akhir.')


def check_component(item, bundle, columns=3):
    require(isinstance(item,dict) and isinstance(item.get('kind'),str) and item['kind'] in KINDS, 'Jenis komponen tidak tersedia.')
    exact_keys(item, new_component(kind=item['kind']).keys(), 'komponen')
    require(isinstance(item['id'],str) and bool(re.fullmatch('[a-f0-9]{32}',item['id'])), 'ID komponen tidak sah.')
    require(item['dataset'] in bundle.ids, 'Dataset komponen tidak tersedia.')
    require(isinstance(item['kind'],str) and isinstance(item['method'],str) and item['kind'] in KINDS and item['method'] in METHODS, 'Jenis komponen/metode tidak tersedia.')
    if item['kind'] in ('pie','donut'):
        require(item['method'] in ('count','count_filled','sum'), 'Pie/donut membutuhkan ukuran aditif: jumlah baris, nilai terisi, atau penjumlahan.')
    for key in ('title','description','question','unit','period','section'):
        string(item[key], key, 1000 if key in ('description','question') else 200)
    string(item['note'], 'Catatan', 5000)
    for key in ('dimension','value_column'):
        require(item[key] is None or isinstance(item[key],str) and len(item[key])<=100, 'Nama kolom tidak sah.')
    require(item['dimension'] not in PRIVATE_COLUMNS, 'Dimensi identitas pribadi disembunyikan.')
    require(item['granularity'] in ('category','day','month','year'), 'Pengelompokan waktu tidak sah.')
    if item['kind'] == 'pivot':
        pivot = item['pivot']
        exact_keys(pivot, ('column','granularity','visualization'), 'pivot')
        string(pivot['column'], 'Kolom pivot', 100)
        require(bool(item['dimension']) and bool(pivot['column']) and item['dimension'] != pivot['column'], 'Baris dan kolom pivot wajib dipilih dan berbeda.')
        require(pivot['column'] not in PRIVATE_COLUMNS, 'Kolom identitas pribadi tidak boleh menjadi dimensi pivot.')
        require(pivot['granularity'] in ('category','day','month','year'), 'Pengelompokan waktu kolom pivot tidak sah.')
        require(isinstance(pivot['visualization'],str) and pivot['visualization'] in PIVOT_VISUALS, 'Visualisasi pivot tidak tersedia.')
        if pivot['visualization']=='stacked':
            require(item['method'] in ('count','count_filled','sum'), 'Batang bertumpuk membutuhkan jumlah baris, nilai terisi, atau penjumlahan.')
    check_color(item['color'])
    integer(item['decimals'],0,4,'Desimal')
    for key in ('row','position'):
        integer(item[key],1,1000,key)
    integer(item['span'],1,3,'Lebar')
    require(isinstance(item['local_filters'],list) and len(item['local_filters'])<=20, 'Terlalu banyak filter lokal.')
    for rule in item['local_filters']:
        check_filter(rule,bundle)
    for key in ('numerator','denominator'):
        require(isinstance(item[key],list) and len(item[key])<=10, 'Kondisi persentase tidak sah.')
        for condition in item[key]:
            exact_keys(condition,('column','operator','value'),'kondisi persentase')
            string(condition['column'],'Kolom kondisi',100)
            require(condition['column'] not in PRIVATE_COLUMNS, 'Kondisi identitas pribadi tidak diperbolehkan.')
            require(isinstance(condition['operator'],str) and condition['operator'] in OPERATORS, 'Operator tidak sah.')
            val = condition['value']
            require(val is None or type(val) in (str,int,float,bool,list), 'Nilai kondisi tidak sah.')
            if isinstance(val,list):
                require(len(val)<=1000 and all(type(x) in (str,int,float,bool) for x in val),'Daftar kondisi tidak sah.')
            for scalar_value in val if isinstance(val,list) else [val]:
                if isinstance(scalar_value,str):
                    string(scalar_value,'Nilai kondisi',300)
                if type(scalar_value) is float:
                    require(math.isfinite(scalar_value),'Nilai kondisi harus angka terbatas.')
            if condition['operator']=='in':
                require(isinstance(val,list),'Operator in membutuhkan daftar nilai.')
    frame = bundle.frame(item['dataset'])
    if item['method'] in NUMERIC_METHODS and item['value_column'] in frame:
        require(item['value_column'] in numeric_columns(frame), 'Metode angka tidak boleh dipakai untuk identitas atau keterangan dengan satuan campuran.')
    if item['kind'] == 'line' and item['dimension'] in frame:
        require(pd.api.types.is_datetime64_any_dtype(frame[item['dimension']]) or pd.api.types.is_numeric_dtype(frame[item['dimension']]), 'Grafik garis membutuhkan tanggal atau urutan angka yang jelas.')


def validate_design(design, bundle):
    exact_keys(design, ('schema_version','group_name','dataset_ref','processing','dashboard','components','filters'), 'desain')
    require(type(design['schema_version']) is int and design['schema_version']==SCHEMA_VERSION, 'Versi skema desain tidak didukung.')
    string(design['group_name'],'Nama kelompok',120)
    require(design['dataset_ref']==dataset_reference(bundle), 'Versi atau sidik dataset berbeda; desain harus memakai dataset bersama yang persis sesuai.')
    require(design['processing']==bundle.manifest['processing'], 'Aturan pengolahan/tanggal acuan berbeda dari dataset bersama.')
    dash=design['dashboard']
    exact_keys(dash, ('village','title','description','primary_color','columns','logo'), 'identitas dashboard')
    for key in ('village','title','description'):
        string(dash[key],key,1000)
    check_color(dash['primary_color'])
    integer(dash['columns'],1,3,'Jumlah kolom')
    if dash['logo'] is not None:
        import base64
        from io import BytesIO
        from PIL import Image
        require(isinstance(dash['logo'],str) and len(dash['logo'])<=400000, 'Logo terlalu besar.')
        try:
            binary=base64.b64decode(dash['logo'],validate=True)
            with Image.open(BytesIO(binary)) as image:
                require(image.format in ('PNG','JPEG') and image.width<=2000 and image.height<=2000,'Logo harus PNG/JPEG maksimal 2000 piksel.')
                image.verify()
        except (ValueError,OSError) as exc:
            raise DesignError('Logo tidak sah.') from exc
    require(isinstance(design['components'],list) and len(design['components'])<=80, 'Desain dibatasi 80 komponen.')
    require(isinstance(design['filters'],list) and len(design['filters'])<=20, 'Desain dibatasi 20 filter dashboard.')
    for item in design['components']:
        check_component(item,bundle,dash['columns'])
    for rule in design['filters']:
        check_filter(rule,bundle,True)
    for items in (design['components'],design['filters']):
        require(len({x['id'] for x in items})==len(items), 'ID ganda dalam desain tidak diperbolehkan.')
    return design


def export_design(design, bundle):
    validate_design(design,bundle)
    prepared=apply_visual_defaults(deepcopy(design))
    payload=json.dumps(prepared,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')
    require(len(payload)<=MAX_DESIGN_BYTES,'Ukuran desain melebihi 2 MB.')
    return payload


def _unique_pairs(pairs):
    output={}
    for key,value in pairs:
        require(key not in output,'JSON memiliki kunci ganda.')
        output[key]=value
    return output


def import_design(payload):
    require(isinstance(payload,bytes) and len(payload)<=MAX_DESIGN_BYTES,'Desain harus berkas JSON maksimal 2 MB.')
    try:
        design=json.loads(payload.decode('utf-8-sig'),object_pairs_hook=_unique_pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(DesignError('Angka JSON tidak sah.')))
    except (UnicodeDecodeError,json.JSONDecodeError,RecursionError):
        raise DesignError('Berkas bukan JSON UTF-8 yang sah.') from None
    require(isinstance(design,dict) and isinstance(design.get('dataset_ref'),dict),'Referensi dataset tidak ditemukan.')
    version=design['dataset_ref'].get('version')
    require(isinstance(version,str),'Versi dataset wajib diisi.')
    require(len(version)<=120,'Nama versi dataset terlalu panjang.')
    bundle=load_shared(version)
    validate_design(design,bundle)
    return apply_visual_defaults(deepcopy(design)),bundle


def ordered_components(design):
    return sorted(design['components'],key=lambda c:(c['row'],c['position']))


def move_component(design, component_id, offset):
    ordered=ordered_components(design)
    index=next(i for i,x in enumerate(ordered) if x['id']==component_id)
    target=index+offset
    if 0<=target<len(ordered):
        ordered[index],ordered[target]=ordered[target],ordered[index]
        # Reindex slots so ambiguous user-entered ties also become predictable.
        for i,item in enumerate(ordered):
            item['row']=i//design['dashboard']['columns']+1
            item['position']=i%design['dashboard']['columns']+1
        apply_visual_defaults(design)


def duplicate_component(design, component_id):
    item=deepcopy(next(c for c in design['components'] if c['id']==component_id))
    item['id']=uid()
    item['title']+=' (salinan)'
    item['row']=max((c['row'] for c in design['components']),default=0)+1
    item['position']=1
    design['components'].append(item)
    apply_visual_defaults(design)
    return item
