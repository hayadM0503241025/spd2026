from types import MappingProxyType

DATASETS = MappingProxyType({
    'penduduk': 'Data_Penduduk', 'pelayanan': 'Data_Pelayanan',
    'umkm': 'Data_UMKM', 'potensi': 'Potensi_Desa',
})
LABELS = MappingProxyType({
    'penduduk': 'Penduduk', 'pelayanan': 'Pelayanan',
    'umkm': 'UMKM', 'potensi': 'Potensi desa',
})
METHODS = MappingProxyType({
    'count': 'Jumlah baris', 'count_filled': 'Jumlah nilai terisi',
    'nunique': 'Jumlah nilai unik', 'sum': 'Penjumlahan',
    'mean': 'Rata-rata', 'median': 'Median', 'min': 'Minimum',
    'max': 'Maksimum', 'percentage': 'Persentase',
})
KINDS = MappingProxyType({
    'kpi': 'Kartu indikator', 'bar': 'Batang vertikal',
    'hbar': 'Batang horizontal', 'line': 'Grafik garis',
    'pie': 'Pie', 'donut': 'Donut', 'table': 'Tabel ringkasan',
    'note': 'Catatan', 'pivot': 'Pivot · tabel & grafik',
})
PIVOT_VISUALS = MappingProxyType({
    'bar': 'Batang berkelompok', 'stacked': 'Batang bertumpuk',
    'hbar': 'Batang horizontal', 'line': 'Grafik garis',
    'area': 'Grafik area', 'scatter': 'Grafik titik (scatter)',
    'bubble': 'Diagram gelembung (bubble)', 'pie': 'Pie', 'donut': 'Donut',
    'heatmap': 'Peta warna (heatmap)', 'treemap': 'Treemap',
})
PIVOT_ADDITIVE_VISUALS = frozenset({'stacked','area','pie','donut','treemap'})


def pivot_visuals(method):
    return [visual for visual in PIVOT_VISUALS
            if visual not in PIVOT_ADDITIVE_VISUALS or method in ('count','count_filled','sum')]


PRIVATE_COLUMNS = frozenset({'nik', 'no_kk', 'nama', 'nama_lengkap', 'tanggal_lahir', 'ID'})
NUMERIC_METHODS = frozenset({'sum', 'mean', 'median', 'min', 'max'})
NON_MEASURES = frozenset({'ID', 'nik', 'no_kk', 'latitude', 'longitude', 'keterangan'})
OPERATORS = frozenset({'equals', 'not_equals', 'in', 'not_null', 'is_null', 'gte', 'lte'})
MAX_DESIGN_BYTES = 2 * 1024 * 1024
SCHEMA_VERSION = 1
