import pytest
from unittest.mock import AsyncMock, Mock
from app.service.s3_service import FileService


@pytest.mark.asyncio
async def test_generate_timestamp(file_service: FileService):
    result = await file_service._generate_timestamp()  
    assert len(result) == 15  # YYYYMMDDTHHMMSS
    assert "T" in result


@pytest.mark.asyncio
async def test_generate_s3_key_text_file(file_service: FileService, mocker):
    fake_uuid = Mock()
    fake_uuid.__str__ = Mock(return_value="test-uuid")
    mocker.patch("app.service.s3_service.uuid.uuid4", return_value=fake_uuid)
    
    result = await file_service._generate_s3_key("case1", "", "text")  
    assert result.startswith("case1/text_input")
    assert result.endswith(".txt")


@pytest.mark.asyncio
async def test_generate_s3_key_response_file(file_service: FileService, mocker):
    # Mock _generate_timestamp since it's called internally
    mocker.patch.object(file_service, '_generate_timestamp', return_value="20240101T120000")
    
    result = await file_service._generate_s3_key("case1", "", "response")  
    assert result == "case1/response_20240101T120000.json"


@pytest.mark.asyncio
async def test_prepare_response_content_dict(file_service: FileService):
    response = {"key": "value"}
    result = await file_service._prepare_response_content(response)  
    assert result == '{"key": "value"}'


@pytest.mark.asyncio
async def test_caching_not_pdf(file_service: FileService, mocker):
    # Mock the caching service methods
    mocker.patch.object(file_service.caching_service, "set_str", new_callable=AsyncMock)
    
    await file_service._cache_pdf(b"content", "text.txt") 
    
    file_service.caching_service.set_str.assert_not_called()


@pytest.mark.asyncio
async def test_caching_pdf_success(file_service: FileService, mocker):
    # Mock PdfReader
    mock_page = Mock()
    mock_page.extract_text.return_value = "extracted text"
    
    mock_reader = Mock()
    mock_reader.pages = [mock_page]
    
    mocker.patch("app.service.s3_service.PdfReader", return_value=mock_reader)
    mocker.patch.object(file_service.caching_service, "set_str", new_callable=AsyncMock)
    
    await file_service._cache_pdf(b"pdf content", "document.pdf")  
    file_service.caching_service.set_str.assert_called_once_with(
        "pdf:text:document.pdf", 
        "extracted text", 
        ttl_seconds=86400
    )


@pytest.mark.asyncio
async def test_generate_file_s3_key(file_service: FileService):
    result = await file_service._generate_file_s3_key("case123", "document.pdf", "20240101T120000")
    assert result == "case123/document_20240101T120000.pdf"


@pytest.mark.asyncio
async def test_generate_file_s3_key_no_extension(file_service: FileService):
    result = await file_service._generate_file_s3_key("case123", "document", "20240101T120000")
    assert result == "case123/document_20240101T120000"


@pytest.mark.asyncio
async def test_generate_file_s3_key_empty_filename(file_service: FileService):
    result = await file_service._generate_file_s3_key("case123", "", "20240101T120000")
    assert result == "upload_20240101T120000"