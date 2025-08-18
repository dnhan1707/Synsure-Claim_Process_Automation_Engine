import pytest
from unittest.mock import AsyncMock
from app.service.case_service import CaseService

@pytest.mark.asyncio
async def test_save_uploaded_files_returns_metadata_when_s3_keys_present(case_service: CaseService, mocker):
    # Arrange
    files = ["file1.pdf", "file2.pdf", "file3.pdf"]
    case_id = "test_case_id"
    case_name = "test_case_name"
    response_data_id = "test_response_case_id"

    fake_saved_keys = ["key1", "key2", "key3"] 
    fake_files_key_result = {"success": True, "s3_keys": fake_saved_keys}

    mocker.patch.object(case_service, "file_service")
    case_service.file_service.save_files = AsyncMock(return_value=fake_files_key_result)

    # Act
    result = await case_service.save_uploaded_files(
        files=files,
        case_id=case_id,
        case_name=case_name,
        response_data_id=response_data_id
    )

    # Assert: result has one item per key with correct fields
    expected = [
        {"case_id": case_id, "case_name": case_name, "s3_link": "key1", "response_id": response_data_id},
        {"case_id": case_id, "case_name": case_name, "s3_link": "key2", "response_id": response_data_id},
        {"case_id": case_id, "case_name": case_name, "s3_link": "key3", "response_id": response_data_id},
    ]
    assert result == expected

    # Assert: dependency was called correctly
    case_service.file_service.save_files.assert_awaited_once_with(files=files, case_id=case_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("returned", [
    {},                       # missing s3_keys
    {"success": True},        # still missing s3_keys
    None,                     # not a dict
    "oops",                   # not a dict
])
async def test_save_uploaded_files_returns_empty_list_without_s3_keys(case_service: CaseService, mocker, returned):
    files = ["f1"]
    case_id = "C1"
    case_name = "Name"
    response_id = None

    mocker.patch.object(case_service, "file_service")
    case_service.file_service.save_files = AsyncMock(return_value=returned)

    result = await case_service.save_uploaded_files(
        files=files,
        case_id=case_id,
        case_name=case_name,
        response_data_id=response_id
    )

    assert result == []  # no keys -> empty list
