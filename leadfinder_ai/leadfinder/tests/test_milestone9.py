"""Milestone 9 tests – CSV Export.

Tests the `csv.py` exporter to ensure proper formatting and data extraction.
"""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

import pytest

from leadfinder.exporters.csv import export_csv

class TestExportCsv:
    @pytest.fixture
    def temp_file(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_exports_correct_columns(self, temp_file):
        leads = [
            {
                "name": "Dream Home Realty",
                "followers": 1200,
                "phone": "+919382380980",
                "website": "https://dreamhomerealty.in",
                "whatsapp": True,
                "score": 80,
            }
        ]
        
        filepath = export_csv(leads, temp_file)
        assert filepath == temp_file
        
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == ["business", "followers", "phone", "website", "whatsapp", "score"]
            rows = list(reader)
            
        assert len(rows) == 1
        assert rows[0]["business"] == "Dream Home Realty"
        assert rows[0]["followers"] == "1200"
        assert rows[0]["phone"] == "+919382380980"
        assert rows[0]["website"] == "https://dreamhomerealty.in"
        assert rows[0]["whatsapp"] == "YES"
        assert rows[0]["score"] == "80"

    def test_adds_csv_extension(self):
        # We test writing to a file without .csv
        fd, path = tempfile.mkstemp()
        os.close(fd)
        
        # ensure path doesn't end in .csv
        assert not path.endswith(".csv")
        
        filepath = export_csv([], path)
        assert filepath == path + ".csv"
        
        # cleanup
        if os.path.exists(path):
            os.unlink(path)
        if os.path.exists(filepath):
            os.unlink(filepath)

    def test_handles_missing_fields(self, temp_file):
        leads = [{"name": "Missing Data Co"}]
        export_csv(leads, temp_file)
        
        with open(temp_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        assert rows[0]["business"] == "Missing Data Co"
        assert rows[0]["followers"] == ""
        assert rows[0]["phone"] == ""
        assert rows[0]["website"] == ""
        assert rows[0]["whatsapp"] == "NO"
        assert rows[0]["score"] == "0"
