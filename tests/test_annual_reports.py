# -*- coding: utf-8 -*-
import pytest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from pathlib import Path
from backend.modules.annual_reports.manager import AnnualReportManager

def test_annual_report_manager_list_reports():
    # Test listing reports from local cafef cache
    manager = AnnualReportManager()
    
    # Locate BASE_DIR and set test_pdf_dir inside it
    from backend.modules.annual_reports.manager import BASE_DIR
    test_pdf_dir = BASE_DIR / "data" / "temp_test_pdfs"
    
    # Mock LOCAL_PDF_DIR to point to test_pdf_dir
    with patch("backend.modules.annual_reports.manager.LOCAL_PDF_DIR", test_pdf_dir):
        ticker_dir = test_pdf_dir / "FPT"
        ticker_dir.mkdir(parents=True, exist_ok=True)
        (ticker_dir / "FPT_2024_NAM_BCTN.pdf").write_text("dummy pdf content")
        
        try:
            reports = manager.list_available_reports("FPT")
            assert len(reports) == 1
            assert reports[0]['source'] == 'cafef'
            assert reports[0]['year'] == 2024
            assert reports[0]['quarter'] == 5
            assert reports[0]['file_name'] == "FPT_2024_NAM_BCTN.pdf"
        finally:
            # Cleanup
            if test_pdf_dir.exists():
                import shutil
                shutil.rmtree(test_pdf_dir)

def test_download_from_cafef_success():
    manager = AnnualReportManager()
    
    mock_reports = [
        {
            'title': 'Báo cáo thường niên năm 2024',
            'url': 'https://cafef.vn/bctn.pdf',
            'filename': 'FPT_2024_NAM_BCTN.pdf',
            'year': 2024,
            'quarter': 5,
            'type': 'annual_report'
        }
    ]
    
    with patch.object(manager.scraper, "fetch_report_metadata", return_value=mock_reports), \
         patch.object(manager.scraper, "download_pdf", return_value=True) as mock_download:
         
        success = manager.download_from_cafef("FPT", 2024, 5)
        assert success is True
        mock_download.assert_called_once()
