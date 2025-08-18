import pytest
from unittest.mock import AsyncMock
from app.service.case_service import CaseService

@pytest.mark.asyncio
async def test_save_uploaded_files_from_contents_returns_metadata_when_s3_keys_present(case_service: CaseService, mocker):
    # Arrange
    file_contents = [
        {"filename": "file1.pdf", "content": b"content1"},
        {"filename": "file2.pdf", "content": b"content2"}
    ]
    case_id = "test_case_id"
    case_name = "test_case_name"
    response_data_id = "test_response_id"

    fake_saved_keys = ["key1", "key2"]
    fake_result = {"s3_keys": fake_saved_keys}

    mocker.patch.object(case_service, "file_service")
    case_service.file_service.save_files_from_bytes = AsyncMock(return_value=fake_result)

    # Act
    result = await case_service.save_uploaded_files_from_contents(
        file_contents=file_contents,
        case_id=case_id,
        case_name=case_name,
        response_data_id=response_data_id
    )

    # Assert
    expected = [
        {"case_id": case_id, "case_name": case_name, "s3_link": "key1", "response_id": response_data_id},
        {"case_id": case_id, "case_name": case_name, "s3_link": "key2", "response_id": response_data_id}
    ]
    assert result == expected
    case_service.file_service.save_files_from_bytes.assert_awaited_once_with(items=file_contents, case_id=case_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("returned", [
    {},                       # missing s3_keys
    {"other_key": "value"},   # wrong key
    {"s3_keys": None},        # s3_keys is None
    {"s3_keys": []},          # s3_keys is empty list
    None,                     # not a dict
    "error"                   # not a dict
])
async def test_save_uploaded_files_from_contents_returns_empty_list_without_s3_keys(case_service: CaseService, mocker, returned):
    file_contents = [{"filename": "test.pdf", "content": b"data"}]
    
    mocker.patch.object(case_service, "file_service")
    case_service.file_service.save_files_from_bytes = AsyncMock(return_value=returned)

    result = await case_service.save_uploaded_files_from_contents(
        file_contents=file_contents,
        case_id="C1",
        case_name="Test",
        response_data_id=None
    )

    assert result == []