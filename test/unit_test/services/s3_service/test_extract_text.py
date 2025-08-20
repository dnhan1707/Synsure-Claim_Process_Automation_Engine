import pytest
from unittest.mock import Mock, patch
from app.service.s3_service import FileService

@pytest.mark.asyncio
async def test_extract_text_success(file_service: FileService):
    # Mock PdfReader and pages
    mock_page1 = Mock()
    mock_page1.extract_text.return_value = "Page 1 text "
    mock_page2 = Mock()
    mock_page2.extract_text.return_value = "Page 2 text"
    
    mock_reader = Mock()
    mock_reader.pages = [mock_page1, mock_page2]
    
    with patch('app.service.s3_service.PdfReader', return_value=mock_reader):
        file_contents = [
            {"content": b"pdf_data_1"},
            {"content": b"pdf_data_2"}
        ]
        
        result = await file_service.extract_text(file_contents)
        
        assert result == "Page 1 text Page 2 textPage 1 text Page 2 text"

@pytest.mark.asyncio
async def test_extract_text_empty_page(file_service: FileService):
    mock_page = Mock()
    mock_page.extract_text.return_value = None  # Some pages return None
    
    mock_reader = Mock()
    mock_reader.pages = [mock_page]
    
    with patch('app.service.s3_service.PdfReader', return_value=mock_reader):
        file_contents = [{"content": b"pdf_data"}]
        result = await file_service.extract_text(file_contents)
        assert result == ""

@pytest.mark.asyncio
async def test_extract_text_exception(file_service: FileService):
    with patch('app.service.s3_service.PdfReader', side_effect=Exception("PDF error")):
        file_contents = [{"content": b"invalid_pdf"}]
        result = await file_service.extract_text(file_contents)
        assert result.startswith("Error extracting text:")