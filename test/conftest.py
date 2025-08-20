import pytest
from unittest.mock import AsyncMock
from app.service.case_service import CaseService
from app.service.s3_service import FileService


@pytest.fixture
def case_service():
    return CaseService()


@pytest.fixture
def file_service():
    return FileService()

# @pytest.fixture
# def async_mock():
#     """
#     Convenience factory for AsyncMock to keep tests tidy.
#     """
#     def _factory(return_value=None, side_effect=None):
#         m = AsyncMock()
#         if side_effect is not None:
#             m.side_effect = side_effect
#         else:
#             m.return_value = return_value
#         return m
#     return _factory
