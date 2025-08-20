import pytest
from unittest.mock import Mock, patch
from app.service.s3_service import FileService

@pytest.mark.asyncio
async def test_create_text_file_and_save_success(file_service: FileService, mocker):
    # Mock dependencies
    mocker.patch.object(file_service, '_generate_s3_key', return_value="case123/text_input_uuid.txt")
    mocker.patch.object(file_service.s3_client, 'put_object')
    
    result = await file_service.create_text_file_and_save("test content", "case123")
    
    assert result == {"success": True, "s3_key": "case123/text_input_uuid.txt"}
    file_service.s3_client.put_object.assert_called_once_with(
        Bucket=file_service.aws_bucket_name,
        Key="case123/text_input_uuid.txt",
        Body="test content".encode("utf-8")
    )

@pytest.mark.asyncio
async def test_create_text_file_and_save_s3_error(file_service: FileService, mocker):
    mocker.patch.object(file_service, '_generate_s3_key', return_value="test_key")
    mocker.patch.object(file_service.s3_client, 'put_object', side_effect=Exception("S3 error"))
    
    result = await file_service.create_text_file_and_save("content", "case123")
    
    assert "error" in result
    assert "S3 error" in result["error"]