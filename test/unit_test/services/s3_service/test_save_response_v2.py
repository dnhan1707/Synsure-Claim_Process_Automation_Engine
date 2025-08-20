import pytest
from unittest.mock import Mock, patch
from app.service.s3_service import FileService

@pytest.mark.asyncio
async def test_save_response_v2_dict_response(file_service: FileService, mocker):
    response = {"result": "success", "data": [1, 2, 3]}
    
    mocker.patch.object(file_service, '_prepare_response_content', return_value='{"result":"success","data":[1,2,3]}')
    mocker.patch.object(file_service, '_generate_s3_key', return_value="case123/response_123.json")
    mocker.patch.object(file_service.s3_client, 'put_object')
    
    result = await file_service.save_respose_v2(response, "case123")
    
    assert result == {"success": True, "s3_key": "case123/response_123.json"}

@pytest.mark.asyncio
async def test_save_response_v2_empty_response(file_service: FileService):
    result = await file_service.save_respose_v2(None, "case123")
    assert result == {"error": "Empty response provided"}
    
    result = await file_service.save_respose_v2("", "case123")
    assert result == {"error": "Empty response provided"}