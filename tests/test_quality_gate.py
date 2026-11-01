"""Unit tests for phase-3 Data Quality. Run: python -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qa_quality_gate import (Reporter, audit_baseline, audit_monthly, audit_part,
                             close_numbers, read_csv_auto, valid_positive_integer_column)


class QualityGateTests(unittest.TestCase):
    def test_separators_comma_and_semicolon(self):
        with tempfile.TemporaryDirectory() as temp:
            for sep in (',', ';'):
                p = Path(temp) / 'sample.csv'
                p.write_text(f'THANG{sep}SO_GHE_BAN\n2024-01{sep}3\n', encoding='utf-8-sig')
                df = read_csv_auto(p)
                self.assertEqual(list(df.columns), ['THANG', 'SO_GHE_BAN'])

    def test_numeric_baseline_allows_int_float(self):
        self.assertTrue(close_numbers(476180, 476180.0))
        self.assertFalse(close_numbers(476180, 476181.0))
        self.assertTrue(close_numbers(float('nan'), float('nan')))
        self.assertFalse(close_numbers(None, 0))

    def test_must_be_positive_integer(self):
        self.assertTrue(valid_positive_integer_column(pd.Series([1, 2.0, 100])))
        self.assertFalse(valid_positive_integer_column(pd.Series([1, 0, 3])))
        self.assertFalse(valid_positive_integer_column(pd.Series([1, 2.5])))

    def test_baseline_same_numbers_different_types_passes(self):
        base = []
        for market in ('Noi dia', 'Quoc te'):
            for i in range(1, 13):
                base.append({'THANG':f'2024-{i:02d}', 'LOAI_CHUYEN_BAY':market,
                             'SO_GHE_BAN':2,'GIA_BINH_QUAN':300.0,
                             'SO_BAN_GHI':476180,'TIEN_TE':'BRL' if market=='Noi dia' else 'USD',
                             'BIEN_DONG_GIA_PCT':0.0})
        old = pd.DataFrame(base)
        cur = old.copy()
        cur['SO_BAN_GHI'] = cur['SO_BAN_GHI'].astype(float)
        report = Reporter()
        audit_baseline(old, cur, report)
        self.assertFalse(report.errors, report.errors)
        cur.loc[0, 'SO_BAN_GHI'] += 1
        fail = Reporter()
        audit_baseline(old, cur, fail)
        self.assertTrue(any('Gia tri baseline' in e for e in fail.errors))

    def test_monthly_rejects_duplicate_keys(self):
        base = {'THANG':'2025-01', 'LOAI_CHUYEN_BAY':'Noi dia',
                'SO_GHE_BAN':3, 'GIA_BINH_QUAN':200,
                'SO_BAN_GHI':3, 'TIEN_TE':'BRL','BIEN_DONG_GIA_PCT':None}
        report = Reporter()
        audit_monthly(pd.DataFrame([base,base]), report, require_full_2024=False)
        self.assertTrue(any('trung khoa' in e.lower() for e in report.errors))

    def test_monthly_rejects_wrong_currency(self):
        base = {'THANG':'2025-01', 'LOAI_CHUYEN_BAY':'Noi dia',
                'SO_GHE_BAN':3, 'GIA_BINH_QUAN':200,
                'SO_BAN_GHI':3, 'TIEN_TE':'USD','BIEN_DONG_GIA_PCT':None}
        report = Reporter()
        audit_monthly(pd.DataFrame([base]), report, require_full_2024=False)
        self.assertTrue(any('tien te' in e.lower() for e in report.errors))

    def test_monthly_does_not_bridge_missing_month(self):
        data = [{'THANG':'2026-04','LOAI_CHUYEN_BAY':'Noi dia','SO_GHE_BAN':3,
                 'GIA_BINH_QUAN':100,'SO_BAN_GHI':3,'TIEN_TE':'BRL','BIEN_DONG_GIA_PCT':None},
                {'THANG':'2026-06','LOAI_CHUYEN_BAY':'Noi dia','SO_GHE_BAN':3,
                 'GIA_BINH_QUAN':120,'SO_BAN_GHI':3,'TIEN_TE':'BRL','BIEN_DONG_GIA_PCT':None}]
        report = Reporter()
        audit_monthly(pd.DataFrame(data), report, require_full_2024=False)
        self.assertFalse(report.errors, report.errors)
        self.assertTrue(any('2026-05' in w for w in report.warnings))
        data[1]['BIEN_DONG_GIA_PCT'] = 20
        report_bad = Reporter()
        audit_monthly(pd.DataFrame(data), report_bad, require_full_2024=False)
        self.assertTrue(any('MoM' in e for e in report_bad.errors))

    def test_part_checks_seats_fare_and_state(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'domestic_2025-01.csv'
            pd.DataFrame([{'THANG':'2025-01', 'LOAI':'Nội địa','ORIGEM':'SBGR',
                           'DESTINO':'SBRJ','ASSENTOS':3,'GIA_NHAN_GHE':900,
                           'GHE_CO_GIA':3}]).to_csv(p,index=False, encoding='utf-8-sig')
            meta={'domestic_2025-01': {'rows':2,'seats':3,
                                        'fare_seats':3,'fare_weight':900}}
            report = Reporter()
            stats = audit_part(p, meta, report)
            self.assertFalse(report.errors, report.errors)
            self.assertEqual(stats['rows'], 2)
            meta['domestic_2025-01']['rows'] = None
            bad = Reporter()
            audit_part(p, meta, bad)
            self.assertTrue(any('rows' in e for e in bad.errors))


if __name__ == '__main__':
    unittest.main()
