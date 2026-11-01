"""Offline tests: python -m unittest discover -s tests -v"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import cap_nhat_anac as m

class ETLTest(unittest.TestCase):
    def test_urls_from_directory_html(self):
        class Resp:
            status_code=200
            text='<html><a href="/sas/tarifadomestica/2025/202501.csv">1</a><a href="202502.csv">2</a><a href="bad.csv">bad</a></html>'
            def raise_for_status(self):pass
        class Session:
            def get(self,*args,**kwargs): return Resp()
        self.assertEqual(set(m.index_files(Session(),'domestic',2025)),{'2025-01','2025-02'})

    def test_numbers(self):
        values=m.num(pd.Series(['629,88','1.250,50','629.88','1,250.50','100','x']))
        self.assertEqual(values.iloc[:5].tolist(),[629.88,1250.50,629.88,1250.50,100])
        self.assertTrue(pd.isna(values.iloc[5]))

    def test_weighted_and_aggregates(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'202501.csv'
            file.write_text('ANO;MES;ORIGEM;DESTINO;TARIFA;ASSENTOS\n2025;1;SBGR;SBRJ;400,00;2\n2025;1;SBGR;SBRJ;800,00;1\n2025;1;SBRJ;SBGR;500,00;3\n',encoding='latin-1')
            routes,info=m.read_chunks(file,'2025-01','domestic')
            self.assertEqual(info['seats'],6)
            self.assertEqual(info['fare_seats'],6)
            self.assertEqual(round(info['fare_weight']/info['fare_seats'],3),516.667)
            self.assertEqual(routes['ASSENTOS'].sum(),6)

    def test_first_update_preserves_2024(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=root/'DuLieu_DaXuLy'; data.mkdir()
            output=m.OUTPUT.copy()
            pd.DataFrame([{'THANG':'2024-01','LOAI_CHUYEN_BAY':'Noi dia','SO_GHE_BAN':2,'GIA_BINH_QUAN':200}]).to_csv(data/output['month'],index=False,encoding='utf-8-sig')
            r=pd.DataFrame([{'ORIGEM':'SBGR','DESTINO':'SBRJ','ASSENTOS':2,'TEN_DI':'Guarulhos','LAT_DI':-23.4,'LON_DI':-46.4,'TEN_DEN':'Santos Dumont','LAT_DEN':-22.9,'LON_DEN':-43.2}])
            r.to_csv(data/output['domestic'],index=False,encoding='utf-8-sig')
            r.to_csv(data/output['international'],index=False,encoding='utf-8-sig')
            pd.DataFrame([{'THANG':'2024-01','DESTINO':'SBRJ','LOAI':'Nội địa','ASSENTOS':2,'TEN_SAN_BAY':'Santos Dumont','THANH_PHO':'Rio de Janeiro','QUOC_GIA':'BR','LAT':-22.9,'LON':-43.2,'DIA_DIEM':'Rio de Janeiro'}]).to_csv(data/output['dest'],index=False,encoding='utf-8-sig')
            baseline=data/'_tu_dong'/'baseline_2024'; baseline.mkdir(parents=True)
            for file in output.values():
                (baseline/file).write_bytes((data/file).read_bytes())
            parts=data/'_tu_dong'/'parts'; parts.mkdir(parents=True)
            pd.DataFrame([{'THANG':'2025-01','LOAI':'Nội địa','ORIGEM':'SBGR','DESTINO':'SBRJ','ASSENTOS':3,'GIA_NHAN_GHE':1600,'GHE_CO_GIA':3}]).to_csv(parts/'domestic_2025-01.csv',index=False,encoding='utf-8-sig')
            air=pd.DataFrame([{'CODE':'SBGR','NAME':'Guarulhos','CITY':'São Paulo','COUNTRY':'BR','LAT':-23.4,'LON':-46.4}, {'CODE':'SBRJ','NAME':'Santos Dumont','CITY':'Rio de Janeiro','COUNTRY':'BR','LAT':-22.9,'LON':-43.2}])
            with patch.multiple(m,DATA=data,AUT=data/'_tu_dong',BASELINE=baseline,PARTS=parts):
                staged=root/'staged';staged.mkdir()
                output=m.build_combined(air,{'months':{'domestic_2025-01':{}}},staged)
                self.assertEqual(set(output['THANG']),{'2024-01','2025-01'})
                self.assertEqual(float(output.loc[output.THANG=='2025-01','GIA_BINH_QUAN'].iloc[0]),1600/3)
                self.assertEqual(len(pd.read_csv(staged/m.OUTPUT['dest'])),2)

if __name__=='__main__': unittest.main()
