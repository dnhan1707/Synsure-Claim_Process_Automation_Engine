import pytest
import uuid
from app.service.supabase_service import SupabaseService

@pytest.mark.integration
@pytest.mark.asyncio
async def test_case_crud_operations(real_supabase_service: SupabaseService, test_environment):
    """Test complete CRUD operations on case table"""
    case_id = str(uuid.uuid4())
    
    # CREATE
    case_data = {
        "id": case_id,
        "case_name": "Integration Test Case",
        "is_active": True
    }
    
    print(f"Creating case with data: {case_data}")
    created_case = await real_supabase_service.insert("case", case_data)
    print(f"Insert result: {created_case}")
    
    # Check if insert returned an error
    if isinstance(created_case, dict) and "error inserting" in created_case:
        pytest.fail(f"Failed to create case: {created_case}")
    
    assert created_case is not None
    assert created_case["id"] == case_id
    assert created_case["case_name"] == "Integration Test Case"
    assert created_case["is_active"] is True
    
    # READ - Test get_all_name_id
    cases = await real_supabase_service.get_all_name_id("case")
    print(f"All active cases: {len(cases)} found")
    case_found = any(case["id"] == case_id for case in cases if case)
    assert case_found, f"Case {case_id} not found in active cases"
    
    # UPDATE
    updated_data = {"case_name": "Updated Integration Test Case"}
    updated_case = await real_supabase_service.update("case", case_id, updated_data)
    print(f"Update result: {updated_case}")
    
    if isinstance(updated_case, dict) and "error" in updated_case:
        pytest.fail(f"Failed to update case: {updated_case}")
    
    assert updated_case["case_name"] == "Updated Integration Test Case"
    
    # DEACTIVATE (cleanup) - set inactive instead of delete
    deactivate_result = await real_supabase_service.update("case", case_id, {"is_active": False})
    assert deactivate_result["is_active"] is False
    
    # Verify case no longer appears in active cases
    active_cases_after = await real_supabase_service.get_all_name_id("case")
    case_still_active = any(case["id"] == case_id for case in active_cases_after)
    assert not case_still_active, "Deactivated case should not appear in active cases"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_response_crud_operations(real_supabase_service: SupabaseService, test_environment):
    """Test response table operations"""
    case_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    
    # Create test case first
    case_data = {"id": case_id, "case_name": "Response Test Case", "is_active": True}
    created_case = await real_supabase_service.insert("case", case_data)
    
    if isinstance(created_case, dict) and "error inserting" in created_case:
        pytest.fail(f"Failed to create case: {created_case}")
    
    # CREATE response
    response_data = {
        "id": response_id,
        "case_id": case_id,
        "s3_link": "test/response/integration_test.json",
        "is_active": True
    }
    
    created_response = await real_supabase_service.insert("response", response_data)
    print(f"Created response: {created_response}")
    
    if isinstance(created_response, dict) and "error inserting" in created_response:
        pytest.fail(f"Failed to create response: {created_response}")
    
    assert created_response["id"] == response_id
    assert created_response["case_id"] == case_id
    assert created_response["s3_link"] == "test/response/integration_test.json"
    
    # READ - Test get_responses_by_case_id
    responses = await real_supabase_service.get_responses_by_case_id(case_id)
    assert len(responses) == 1
    assert responses[0]["s3_link"] == "test/response/integration_test.json"
    
    # READ - Test get_latest_response_by_case_id
    latest_response = await real_supabase_service.get_latest_response_by_case_id(case_id)
    assert latest_response is not None
    assert latest_response["id"] == response_id
    assert latest_response["s3_link"] == "test/response/integration_test.json"
    
    # UPDATE response
    updated_response_data = {"s3_link": "test/response/updated_integration_test.json"}
    updated_response = await real_supabase_service.update("response", response_id, updated_response_data)
    assert updated_response["s3_link"] == "test/response/updated_integration_test.json"
    
    # Cleanup
    await real_supabase_service.update("response", response_id, {"is_active": False})
    await real_supabase_service.update("case", case_id, {"is_active": False})

@pytest.mark.integration
@pytest.mark.asyncio
async def test_files_table_operations(real_supabase_service: SupabaseService, test_environment):
    """Test file metadata operations with proper foreign key relationships"""
    case_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    
    # Create test case first
    case_data = {"id": case_id, "case_name": "File Test Case", "is_active": True}
    created_case = await real_supabase_service.insert("case", case_data)
    
    if isinstance(created_case, dict) and "error inserting" in created_case:
        pytest.fail(f"Failed to create case: {created_case}")
    
    # Create response record to satisfy foreign key constraint
    response_data = {
        "id": response_id,
        "case_id": case_id,
        "s3_link": "test/response/file_test.json",
        "is_active": True
    }
    
    created_response = await real_supabase_service.insert("response", response_data)
    if isinstance(created_response, dict) and "error inserting" in created_response:
        pytest.fail(f"Failed to create response: {created_response}")
    
    # Test bulk file insert
    files_data = [
        {
            "case_id": case_id,
            "case_name": "File Test Case", 
            "s3_link": "test/files/integration_file1.pdf",
            "response_id": response_id,
            "is_active": True
        },
        {
            "case_id": case_id,
            "case_name": "File Test Case",
            "s3_link": "test/files/integration_file2.txt", 
            "response_id": response_id,
            "is_active": True
        }
    ]
    
    result = await real_supabase_service.insert_bulk("files", files_data)
    print(f"Bulk insert result: {result}")
    
    if isinstance(result, dict) and "error" in result:
        pytest.fail(f"Failed to bulk insert files: {result}")
    
    assert len(result) == 2
    
    # Test get_files_by_case_id
    files = await real_supabase_service.get_files_by_case_id(case_id)
    # print(f"Files found for case {case_id}: {len(files)}")
    # print(f"Files data: {files}")
    
    assert len(files) == 2
    assert all("s3_link" in file for file in files)
    
    # Verify s3_links are correct
    s3_links = [file["s3_link"] for file in files]
    assert "test/files/integration_file1.pdf" in s3_links
    assert "test/files/integration_file2.txt" in s3_links
    
    # Cleanup
    for file_record in result:
        await real_supabase_service.update("files", file_record["id"], {"is_active": False})
    await real_supabase_service.update("response", response_id, {"is_active": False})
    await real_supabase_service.update("case", case_id, {"is_active": False})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection(real_supabase_service: SupabaseService, test_environment):
    """Test basic database connectivity"""
    # Simple test to verify connection works
    cases = await real_supabase_service.get_all_name_id("case")
    print(f"Database connection test - found {len(cases)} active cases")
    
    # Should return a list (even if empty)
    assert isinstance(cases, list)
    
    # Each case should have required fields
    for case in cases[:3]:  # Check first 3 cases
        assert "id" in case
        assert "case_name" in case

@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_responses_for_case(real_supabase_service: SupabaseService, test_environment):
    """Test multiple responses for the same case"""
    case_id = str(uuid.uuid4())
    response_id_1 = str(uuid.uuid4())
    response_id_2 = str(uuid.uuid4())
    
    # Create test case
    case_data = {"id": case_id, "case_name": "Multiple Response Test", "is_active": True}
    created_case = await real_supabase_service.insert("case", case_data)
    
    if isinstance(created_case, dict) and "error inserting" in created_case:
        pytest.fail(f"Failed to create case: {created_case}")
    
    # Create first response
    response_data_1 = {
        "id": response_id_1,
        "case_id": case_id,
        "s3_link": "test/response/first_response.json",
        "is_active": True
    }
    
    created_response_1 = await real_supabase_service.insert("response", response_data_1)
    if isinstance(created_response_1, dict) and "error inserting" in created_response_1:
        pytest.fail(f"Failed to create first response: {created_response_1}")
    
    # Wait a moment to ensure different timestamps
    import asyncio
    await asyncio.sleep(0.1)
    
    # Create second response (more recent)
    response_data_2 = {
        "id": response_id_2,
        "case_id": case_id,
        "s3_link": "test/response/second_response.json",
        "is_active": True
    }
    
    created_response_2 = await real_supabase_service.insert("response", response_data_2)
    if isinstance(created_response_2, dict) and "error inserting" in created_response_2:
        pytest.fail(f"Failed to create second response: {created_response_2}")
    
    # Test get_responses_by_case_id returns all responses
    all_responses = await real_supabase_service.get_responses_by_case_id(case_id)
    assert len(all_responses) == 2
    
    s3_links = [resp["s3_link"] for resp in all_responses]
    assert "test/response/first_response.json" in s3_links
    assert "test/response/second_response.json" in s3_links
    
    # Test get_latest_response_by_case_id returns the most recent
    latest_response = await real_supabase_service.get_latest_response_by_case_id(case_id)
    assert latest_response is not None
    assert latest_response["id"] == response_id_2  # Should be the second (most recent)
    assert latest_response["s3_link"] == "test/response/second_response.json"
    
    # Cleanup
    await real_supabase_service.update("response", response_id_1, {"is_active": False})
    await real_supabase_service.update("response", response_id_2, {"is_active": False})
    await real_supabase_service.update("case", case_id, {"is_active": False})

@pytest.mark.integration
@pytest.mark.asyncio
async def test_deduplication_in_get_files_by_case_id(real_supabase_service: SupabaseService, test_environment):
    """Test that get_files_by_case_id properly deduplicates by s3_link"""
    case_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    
    # Create test case and response
    case_data = {"id": case_id, "case_name": "Deduplication Test", "is_active": True}
    created_case = await real_supabase_service.insert("case", case_data)
    
    if isinstance(created_case, dict) and "error inserting" in created_case:
        pytest.fail(f"Failed to create case: {created_case}")
    
    response_data = {
        "id": response_id,
        "case_id": case_id,
        "s3_link": "test/response/dedup_test.json",
        "is_active": True
    }
    
    created_response = await real_supabase_service.insert("response", response_data)
    if isinstance(created_response, dict) and "error inserting" in created_response:
        pytest.fail(f"Failed to create response: {created_response}")
    
    # Create multiple file records with same s3_link (simulate duplicates)
    duplicate_s3_link = "test/files/duplicate_file.pdf"
    files_data = [
        {
            "case_id": case_id,
            "case_name": "Deduplication Test",
            "s3_link": duplicate_s3_link,
            "response_id": response_id,
            "is_active": True
        },
        {
            "case_id": case_id,
            "case_name": "Deduplication Test",
            "s3_link": duplicate_s3_link,  # Same s3_link
            "response_id": response_id,
            "is_active": True
        },
        {
            "case_id": case_id,
            "case_name": "Deduplication Test",
            "s3_link": "test/files/unique_file.pdf",  # Different s3_link
            "response_id": response_id,
            "is_active": True
        }
    ]
    
    result = await real_supabase_service.insert_bulk("files", files_data)
    if isinstance(result, dict) and "error" in result:
        pytest.fail(f"Failed to insert files: {result}")
    
    assert len(result) == 3  # 3 records inserted
    
    # Test deduplication
    files = await real_supabase_service.get_files_by_case_id(case_id)
    
    # Should only return 2 unique s3_links despite 3 records
    assert len(files) == 2
    
    s3_links = [file["s3_link"] for file in files]
    assert duplicate_s3_link in s3_links
    assert "test/files/unique_file.pdf" in s3_links
    
    # Cleanup
    for file_record in result:
        await real_supabase_service.update("files", file_record["id"], {"is_active": False})
    await real_supabase_service.update("response", response_id, {"is_active": False})
    await real_supabase_service.update("case", case_id, {"is_active": False})

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_and_edge_cases(real_supabase_service: SupabaseService, test_environment):
    """Test error handling and edge cases"""
    
    # Test get operations with non-existent case_id
    non_existent_case_id = str(uuid.uuid4())
    
    files = await real_supabase_service.get_files_by_case_id(non_existent_case_id)
    assert files == []  # Should return empty list
    
    responses = await real_supabase_service.get_responses_by_case_id(non_existent_case_id)
    assert responses == []  # Should return empty list
    
    latest_response = await real_supabase_service.get_latest_response_by_case_id(non_existent_case_id)
    assert latest_response is None  # Should return None
    
    # Test update with non-existent ID
    non_existent_id = str(uuid.uuid4())
    update_result = await real_supabase_service.update("case", non_existent_id, {"case_name": "Non-existent"})
    assert update_result is None  # Should return None
    
    # Test insert with duplicate ID (should fail)
    case_id = str(uuid.uuid4())
    case_data = {"id": case_id, "case_name": "Duplicate Test", "is_active": True}
    
    # First insert should succeed
    first_insert = await real_supabase_service.insert("case", case_data)
    assert first_insert is not None
    
    # Second insert with same ID should fail
    second_insert = await real_supabase_service.insert("case", case_data)
    if isinstance(second_insert, dict) and "error inserting" in second_insert:
        assert "duplicate" in second_insert["error inserting"].lower() or "unique" in second_insert["error inserting"].lower()
    
    # Cleanup
    await real_supabase_service.update("case", case_id, {"is_active": False})