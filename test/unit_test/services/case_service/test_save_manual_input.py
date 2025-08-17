import pytest 
from unittest.mock import AsyncMock
from app.service.case_service import CaseService

@pytest.mark.asyncio
async def test_save_manual_input_returns_metadata_when_s3_key_present(
    case_service: CaseService,
    mocker
):
    # Arrange
    manual_inputs = "hello world"
    case_id = "CASE123"
    case_name = "Sample Case"
    response_id = "RESP42"

    # Mock the file_service method to simulate a successful write that returns a key
    fake_result = {"s3_key": "s3://bucket/cases/CASE123/manual.txt"}
    create_mock = AsyncMock(return_value=fake_result)
    mocker.patch.object(case_service, "file_service")
    case_service.file_service.create_text_file_and_save = create_mock

    # Act
    result = await case_service.save_manual_input(
        manual_inputs=manual_inputs,
        case_id=case_id,
        case_name=case_name,
        response_data_id=response_id
    )


    # Assert: correct shape and data
    assert result == {
        "case_id": case_id,
        "case_name": case_name,
        "s3_link": fake_result["s3_key"],
        "response_id": response_id
    }
    # Assert: collaborator called with expected args
    create_mock.assert_awaited_once_with(content=manual_inputs, case_id=case_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("returned", [
    {},                       # missing key
    {"not_key": "value"},     # wrong key
    None,                     # not a dict
    "error"                   # not a dict
])
async def test_save_manual_input_returns_none_without_s3_key(case_service: CaseService, mocker, returned):
    # Arrange
    mocker.patch.object(case_service, "file_service")  # this create a fake case_service.file_service so we will not trigger the real function in file_service
    case_service.file_service.create_text_file_and_save = AsyncMock(return_value=returned)

    # Act
    result = await case_service.save_manual_input(
        manual_inputs="text",
        case_id="C1",
        case_name="Case",
        response_data_id=None
    )

    # Assert
    assert result is None