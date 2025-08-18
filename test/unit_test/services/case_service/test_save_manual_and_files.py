import pytest
from unittest.mock import AsyncMock
from app.service.case_service import CaseService

@pytest.mark.asyncio
async def test_save_manual_and_files_with_manual_input_only(case_service: CaseService, mocker):
    # Arrange
    manual_input = "test manual input"
    case_id = "C123"
    case_name = "Test Case"
    response_data_id = "R456"

    text_file_result = {"case_id": case_id, "case_name": case_name, "s3_link": "manual.txt", "response_id": response_data_id}
    
    mocker.patch.object(case_service, "save_manual_input")
    case_service.save_manual_input = AsyncMock(return_value=text_file_result)
    
    mocker.patch.object(case_service, "sp_service")
    case_service.sp_service.insert_bulk = AsyncMock()

    # Act
    await case_service.save_manual_and_files(
        case_id=case_id,
        case_name=case_name,
        manual_inputs=manual_input,
        files=None,
        response_data_id=response_data_id
    )

    # Assert
    case_service.save_manual_input.assert_awaited_once_with(manual_input, case_id, case_name, response_data_id)
    case_service.sp_service.insert_bulk.assert_awaited_once_with(table_name="files", objects=[text_file_result])


@pytest.mark.asyncio
async def test_save_manual_and_files_with_file_contents(case_service: CaseService, mocker):
    # Arrange
    file_contents = [{"filename": "test.pdf", "content": b"data"}]
    case_id = "C123"
    case_name = "Test Case"
    response_data_id = "R456"

    uploaded_files_result = [{"case_id": case_id, "case_name": case_name, "s3_link": "file.pdf", "response_id": response_data_id}]
    
    mocker.patch.object(case_service, "save_uploaded_files_from_contents")
    case_service.save_uploaded_files_from_contents = AsyncMock(return_value=uploaded_files_result)
    
    mocker.patch.object(case_service, "sp_service")
    case_service.sp_service.insert_bulk = AsyncMock()

    # Act
    await case_service.save_manual_and_files(
        case_id=case_id,
        case_name=case_name,
        manual_inputs="",
        files=None,
        response_data_id=response_data_id,
        file_contents=file_contents
    )

    # Assert
    case_service.save_uploaded_files_from_contents.assert_awaited_once_with(file_contents, case_id, case_name, response_data_id)
    case_service.sp_service.insert_bulk.assert_awaited_once_with(table_name="files", objects=uploaded_files_result)


@pytest.mark.asyncio
async def test_save_manual_and_files_with_upload_files(case_service: CaseService, mocker):
    # Arrange
    files = ["mock_file1", "mock_file2"]  # Mock UploadFile objects
    case_id = "C123"
    case_name = "Test Case"
    response_data_id = "R456"

    uploaded_files_result = [
        {"case_id": case_id, "case_name": case_name, "s3_link": "file1.pdf", "response_id": response_data_id},
        {"case_id": case_id, "case_name": case_name, "s3_link": "file2.pdf", "response_id": response_data_id}
    ]
    
    mocker.patch.object(case_service, "save_uploaded_files")
    case_service.save_uploaded_files = AsyncMock(return_value=uploaded_files_result)
    
    mocker.patch.object(case_service, "sp_service")
    case_service.sp_service.insert_bulk = AsyncMock()

    # Act
    await case_service.save_manual_and_files(
        case_id=case_id,
        case_name=case_name,
        manual_inputs="",
        files=files,
        response_data_id=response_data_id
    )

    # Assert
    case_service.save_uploaded_files.assert_awaited_once_with(files, case_id, case_name, response_data_id)
    case_service.sp_service.insert_bulk.assert_awaited_once_with(table_name="files", objects=uploaded_files_result)


@pytest.mark.asyncio
async def test_save_manual_and_files_no_files_to_insert(case_service: CaseService, mocker):
    # Arrange
    mocker.patch.object(case_service, "save_manual_input")
    case_service.save_manual_input = AsyncMock(return_value=None)  # No file created
    
    mocker.patch.object(case_service, "sp_service")
    case_service.sp_service.insert_bulk = AsyncMock()

    # Act
    await case_service.save_manual_and_files(
        case_id="C123",
        case_name="Test",
        manual_inputs="test",
        files=None,
        response_data_id="R456"
    )

    # Assert
    case_service.sp_service.insert_bulk.assert_not_awaited()