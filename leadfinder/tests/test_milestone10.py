"""Milestone 10 tests – TXT Export.

Tests the `txt.py` exporter to ensure correct formatting of text blocks.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from leadfinder.exporters.txt import export_txt

class TestExportTxt:
    @pytest.fixture
    def temp_file(self):
        fd, path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_exports_correct_format(self, temp_file):
        leads = [
            {
                "name": "Dream Home Realty",
                "followers": 9,
                "phone": "+919382380980",
                "website": None,
                "whatsapp": True,
                "score": 98,
            }
        ]
        
        filepath = export_txt(leads, temp_file)
        assert filepath == temp_file
        
        with open(filepath, mode="r", encoding="utf-8") as f:
            content = f.read()
            
        assert "Business\nDream Home Realty\n" in content
        assert "Followers\n9\n" in content
        assert "Phone\n+919382380980\n" in content
        assert "WhatsApp\nYES\n" in content
        assert "Website\nNO\n" in content
        assert "Score\n98\n" in content
        assert "--------------------------------" in content

    def test_adds_txt_extension(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        
        assert not path.endswith(".txt")
        
        filepath = export_txt([], path)
        assert filepath == path + ".txt"
        
        if os.path.exists(path):
            os.unlink(path)
        if os.path.exists(filepath):
            os.unlink(filepath)

    def test_handles_missing_fields(self, temp_file):
        leads = [{"name": "Missing Data Co"}]
        export_txt(leads, temp_file)
        
        with open(temp_file, mode="r", encoding="utf-8") as f:
            content = f.read()
            
        assert "Business\nMissing Data Co\n" in content
        assert "Followers\nUnknown\n" in content
        assert "Phone\nNone\n" in content
        assert "WhatsApp\nNO\n" in content
        assert "Website\nNO\n" in content
        assert "Score\n0\n" in content
