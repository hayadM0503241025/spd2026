import pandas as pd
import pytest
from studio.aggregation import count_pivot, calculate, IndicatorError


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
