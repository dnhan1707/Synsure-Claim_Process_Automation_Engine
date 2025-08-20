import pytest
from unittest.mock import Mock, patch
from app.service.s3_service import FileService


@pytest.mark.asyncio
async def test_save_files_success(file_service: FileService, mocker):
    # Create mock files
    mock_file1 = mocker.Mock()
    mock_file1.filename = "doc1.pdf"
    mock_file1.seek = mocker.AsyncMock()
    mock_file1.read = mocker.AsyncMock(return_value=b"file1_content")
    
    mock_file2 = mocker.Mock()
    mock_file2.filename = "doc2.txt"
    mock_file2.seek = mocker.AsyncMock()
    mock_file2.read = mocker.AsyncMock(return_value=b"file2_content")
    
    files = [mock_file1, mock_file2]
    
    # Mock dependencies
    mocker.patch.object(file_service, '_generate_timestamp', return_value="20240101T120000")
    mocker.patch.object(file_service, '_generate_file_s3_key', side_effect=["key1", "key2"])
    mocker.patch.object(file_service.s3_client, 'upload_fileobj')
    mocker.patch.object(file_service, '_cache_pdf')
    
    result = await file_service.save_files(files, "case123")
    
    assert result == {"success": True, "s3_keys": ["key1", "key2"]}
    assert file_service.s3_client.upload_fileobj.call_count == 2

@pytest.mark.asyncio
async def test_save_files_empty_list(file_service: FileService):
    result = await file_service.save_files([], "case123")
    assert result == {"success": True, "s3_keys": []}

@pytest.mark.asyncio
async def test_save_files_empty_file_content(file_service: FileService, mocker):
    mock_file = mocker.Mock()
    mock_file.filename = "empty.txt"
    mock_file.seek = mocker.AsyncMock()
    mock_file.read = mocker.AsyncMock(return_value=b"")  # Empty content
    
    mocker.patch.object(file_service, '_generate_timestamp', return_value="20240101T120000")
    
    result = await file_service.save_files([mock_file], "case123")
    
    assert result == {"success": True, "s3_keys": []}