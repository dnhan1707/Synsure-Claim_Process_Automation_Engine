import pytest
from unittest.mock import Mock, patch
from app.service.s3_service import FileService


@pytest.mark.asyncio
async def test_save_files_from_bytes_success(file_service: FileService, mocker):
    items = [
        {"filename": "doc1.pdf", "content": b"pdf_content"},
        {"filename": "doc2.txt", "content": b"txt_content"}
    ]
    
    mocker.patch.object(file_service, '_generate_timestamp', return_value="20240101T120000")
    mocker.patch.object(file_service, '_generate_file_s3_key', side_effect=["key1", "key2"])
    mocker.patch.object(file_service.s3_client, 'put_object')
    mocker.patch.object(file_service, '_cache_pdf')
    
    result = await file_service.save_files_from_bytes(items, "case123")
    
    assert result == {"success": True, "s3_keys": ["key1", "key2"]}
    assert file_service.s3_client.put_object.call_count == 2

@pytest.mark.asyncio
async def test_save_files_from_bytes_invalid_items(file_service: FileService, mocker):
    items = [
        {"filename": "", "content": b"content"},  # Empty filename
        {"filename": "test.txt", "content": None},  # No content
        {}  # Missing keys
    ]
    
    mocker.patch.object(file_service, '_generate_timestamp', return_value="20240101T120000")
    
    result = await file_service.save_files_from_bytes(items, "case123")
    
    assert result == {"success": True, "s3_keys": []}
