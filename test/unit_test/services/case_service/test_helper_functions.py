import pytest
from unittest.mock import AsyncMock
from app.service.case_service import CaseService

@pytest.mark.asyncio
async def test_aggregate_file_contents_from_metadata(case_service: CaseService, mocker):
    # Arrange
    files_metadata = [
        {"s3_link": "bucket/case1/file.pdf", "case_name": "Test"},
        {"s3_link": "bucket/case1/manual.txt", "case_name": "Test"}
    ]
    
    # Mock dependencies using AsyncMock consistently
    case_service.file_service.extract_pdf_text_cached_from_s3 = AsyncMock(return_value="PDF content")
    case_service._load_text_from_s3 = AsyncMock(return_value="Manual input")
    
    # Act
    manual_input, aggregated_details = await case_service._aggregate_file_contents_from_metadata(files_metadata)
    
    # Assert
    assert manual_input == "Manual input"
    assert aggregated_details == "PDF content"


@pytest.mark.asyncio
async def test_load_text_from_s3_success(case_service: CaseService, mocker):
    # Mock S3 client
    mock_s3_obj = {"Body": mocker.Mock()}
    mock_s3_obj["Body"].read.return_value = b"test content"
    
    mocker.patch.object(case_service.file_service.s3_client, 'get_object', return_value=mock_s3_obj)
    
    result = await case_service._load_text_from_s3("test/key")
    
    assert result == "test content"


@pytest.mark.asyncio
async def test_load_text_from_s3_exception_returns_empty(case_service: CaseService, mocker):
    mocker.patch.object(case_service.file_service.s3_client, 'get_object', side_effect=Exception("S3 error"))
    
    result = await case_service._load_text_from_s3("test/key")
    
    assert result == ""


@pytest.mark.asyncio
async def test_link_existing_files_to_response(case_service: CaseService, mocker):
    # Arrange
    files_metadata = [
        {"s3_link": "key1", "case_name": "Test1"},
        {"s3_link": "key2", "case_name": "Test2"}
    ]
    case_id = "C123"
    response_data_id = "R456"
    
    # Mock using AsyncMock for consistency
    case_service.sp_service.insert_bulk = AsyncMock()
    
    # Act
    await case_service._link_existing_files_to_response(files_metadata, case_id, response_data_id)
    
    # Assert
    expected_files = [
        {"case_id": "C123", "case_name": "Test1", "s3_link": "key1", "response_id": "R456"},
        {"case_id": "C123", "case_name": "Test2", "s3_link": "key2", "response_id": "R456"}
    ]
    case_service.sp_service.insert_bulk.assert_awaited_once_with(
        table_name="files", 
        objects=expected_files
    )
