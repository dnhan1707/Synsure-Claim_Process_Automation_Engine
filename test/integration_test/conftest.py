import pytest 
from app.config.settings import get_settings
from app.service.s3_service import FileService
from app.service.supabase_service import SupabaseService


@pytest.fixture(scope="session")
def test_environment():
    settings = get_settings()
    assert settings.env == "development"
    return settings


@pytest.fixture
def real_supabase_service() -> SupabaseService:
    sp_service = SupabaseService()
    return sp_service


@pytest.fixture
def real_s3_service() -> FileService:
    s3_service = FileService()
    return s3_service

