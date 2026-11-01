"""Integration tests on synthetic DuckDB: add/replace/metadata/no-op/rollback."""
import contextlib
import csv
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

MODULE_PATH = Path(__file__).resolve().parents[1] / "data_warehouse" / "incremental_warehouse.py"
SPEC = importlib.util.spec_from_file_location("anac_incremental_warehouse", MODULE_PATH)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class IncrementalWarehouseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.db = root / "anac.duckdb"
        self.parts = root / "parts"
        self.parts.mkdir()
        self.state_file = root / "state.json"
        self.state = {"months": {}}
        with duckdb.connect(str(self.db)) as conn:
            conn.execute("""
                CREATE TABLE dim_month (month_key INTEGER PRIMARY KEY, sale_year INTEGER,
                    sale_month INTEGER, sale_quarter INTEGER);
                CREATE TABLE dim_market (market_key INTEGER PRIMARY KEY, market_code VARCHAR,
                    market_name VARCHAR, currency_code VARCHAR);
                INSERT INTO dim_market VALUES (1,'domestic','Noi dia','BRL'),
                                              (2,'international','Quoc te','USD');
                CREATE TABLE dim_airport (airport_code VARCHAR PRIMARY KEY,
                    airport_name VARCHAR, municipality VARCHAR, country_code VARCHAR,
                    latitude DOUBLE, longitude DOUBLE);
                CREATE TABLE fact_airfare_route_monthly (
                    month_key INTEGER REFERENCES dim_month(month_key),
                    market_key INTEGER REFERENCES dim_market(market_key),
                    origin_airport_code VARCHAR REFERENCES dim_airport(airport_code),
                    destination_airport_code VARCHAR REFERENCES dim_airport(airport_code),
                    total_seats BIGINT, priced_seats BIGINT, fare_weighted_sum DOUBLE,
                    source_record_count BIGINT,
                    PRIMARY KEY(month_key, market_key, origin_airport_code, destination_airport_code)
                );
                CREATE TABLE etl_month_metadata (
                    month_key INTEGER, market_key INTEGER, source_record_count BIGINT,
                    source_file VARCHAR, PRIMARY KEY (month_key, market_key)
                );
                CREATE VIEW vw_monthly_kpi AS
                SELECT f.month_key, m.market_code,
                    COALESCE(e.source_record_count, SUM(f.source_record_count)) AS source_record_count
                FROM fact_airfare_route_monthly f
                JOIN dim_market m ON m.market_key=f.market_key
                LEFT JOIN etl_month_metadata e
                  ON e.month_key=f.month_key AND e.market_key=f.market_key
                GROUP BY f.month_key,m.market_code,e.source_record_count;
                INSERT INTO dim_month VALUES (202401,2024,1,1);
                INSERT INTO dim_airport(airport_code) VALUES ('SBGR'), ('SBRJ');
                INSERT INTO fact_airfare_route_monthly VALUES
                   (202401,1,'SBGR','SBRJ',500,500,25000.0,50);
            """)

    def write_part(self, period="2025-01", seats=(10,20), rows=5, fare=(500.,1000.)):
        key = "domestic_" + period
        path = self.parts / (key + ".csv")
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["THANG", "LOAI", "ORIGEM", "DESTINO", "ASSENTOS", "GIA_NHAN_GHE", "GHE_CO_GIA"])
            writer.writerow([period,"Nội địa","SBGR","SBRJ",seats[0],fare[0],seats[0]])
            writer.writerow([period,"Nội địa","SBGR","SBSP",seats[1],fare[1],seats[1]])
        self.state["months"][key] = {
            "month": period, "market": "domestic", "rows": rows,
            "seats": sum(seats), "fare_seats": sum(seats), "fare_weight": sum(fare)
        }
        self.state_file.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        return path

    def run_script(self, mode):
        with contextlib.redirect_stdout(io.StringIO()):
            return mod.main(["--db", str(self.db), "--parts-dir", str(self.parts),
                             "--state-file", str(self.state_file), mode])

    def count(self, month=202501):
        with duckdb.connect(str(self.db), read_only=True) as conn:
            return conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(total_seats),0) FROM fact_airfare_route_monthly
                WHERE month_key = ?
            """, [month]).fetchone()

    def metadata(self, month=202501):
        with duckdb.connect(str(self.db), read_only=True) as conn:
            return conn.execute("""
                SELECT source_record_count FROM vw_monthly_kpi
                WHERE month_key = ? AND market_code = 'domestic'
            """, [month]).fetchone()[0]

    def test_incremental_add_noop_update_metadata_and_replace(self):
        self.write_part()
        self.run_script("--check")
        self.assertEqual(self.count(), (0, 0))
        self.run_script("--apply")
        self.assertEqual(self.count(), (2, 30))
        self.assertEqual(self.metadata(), 5)
        self.assertEqual(self.count(202401), (1, 500))
        self.run_script("--apply")  # no duplicates
        self.assertEqual(self.count(), (2, 30))
        self.state["months"]["domestic_2025-01"]["rows"] = 6
        self.state_file.write_text(json.dumps(self.state), encoding="utf-8")
        self.run_script("--apply")  # metadata only
        self.assertEqual(self.count(), (2, 30))
        self.assertEqual(self.metadata(), 6)
        self.write_part(seats=(12,20), rows=7, fare=(600.,1000.))
        self.run_script("--apply")  # replace one month
        self.assertEqual(self.count(), (2, 32))
        self.assertEqual(self.metadata(), 7)
        self.assertEqual(self.count(202401), (1, 500))

    def test_existing_month_is_seeded_without_reinserting_fact(self):
        self.write_part()
        with duckdb.connect(str(self.db)) as conn:
            conn.execute("INSERT INTO dim_month VALUES (202501,2025,1,1)")
            conn.execute("INSERT INTO dim_airport(airport_code) VALUES ('SBSP')")
            conn.execute("""
                INSERT INTO fact_airfare_route_monthly VALUES
                   (202501,1,'SBGR','SBRJ',10,10,500.0,NULL),
                   (202501,1,'SBGR','SBSP',20,20,1000.0,NULL)
            """)
            conn.execute("""
                INSERT INTO etl_month_metadata VALUES
                    (202501,1,5,'domestic_2025-01.csv')
            """)
        self.run_script("--apply")
        self.assertEqual(self.count(), (2, 30))
        self.run_script("--apply")
        self.assertEqual(self.count(), (2, 30))
        with duckdb.connect(str(self.db), read_only=True) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM etl_part_sync').fetchone()[0], 1)

    def test_invalid_part_rolls_back(self):
        self.write_part()
        self.run_script("--apply")
        self.write_part(seats=(-1,20), rows=8, fare=(500.,1000.))
        with self.assertRaises(ValueError):
            self.run_script("--apply")
        self.assertEqual(self.count(), (2, 30))
        self.assertEqual(self.metadata(), 5)

    def test_missing_state_fails_before_modify(self):
        self.write_part()
        self.state_file.write_text('{"months":{}}', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.run_script("--apply")
        self.assertEqual(self.count(), (0, 0))

    def test_parse_rows(self):
        self.assertEqual(mod.parse_rows("725702", "sample"), 725702)
        self.assertIsNone(mod.parse_rows(None, "sample"))
        with self.assertRaises(ValueError):
            mod.parse_rows("not-an-int", "sample")


if __name__ == "__main__":
    unittest.main()
