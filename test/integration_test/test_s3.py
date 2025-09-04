import pytest
import os
import io
from app.service.s3_service import FileService

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_text_file_and_save(real_s3_service: FileService, test_environment):
    """Test creating and saving text content to S3"""
    test_content = "This is integration test content for S3"
    case_id = "integration-test-case"
    
    # Save text file
    result = await real_s3_service.create_text_file_and_save(test_content, case_id)
    
    assert result["success"] is True
    assert "s3_key" in result
    
    s3_key = result["s3_key"]
    print(f"Created text file with S3 key: {s3_key}")
    
    # Verify file exists in S3 and retrieve content
    s3_obj = real_s3_service.s3_client.get_object(
        Bucket=real_s3_service.aws_bucket_name,
        Key=s3_key
    )
    retrieved_content = s3_obj["Body"].read().decode("utf-8")
    assert retrieved_content == test_content
    
    # Cleanup
    real_s3_service.s3_client.delete_object(
        Bucket=real_s3_service.aws_bucket_name,
        Key=s3_key
    )

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_files_from_bytes(real_s3_service: FileService, test_environment):
    """Test saving files from byte content"""
    case_id = "integration-test-case"
    
    # Read test files
    txt_path = "test/test_data/case/text1.txt"
    pdf_path = "test/test_data/case/file1.pdf"
    
    # Check if files exist
    if not os.path.exists(txt_path) or not os.path.exists(pdf_path):
        pytest.skip("Test files not found")
    
    # Read file contents
    with open(txt_path, "rb") as f:
        txt_content = f.read()
    
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    
    test_files = [
        {"filename": "test_text.txt", "content": txt_content},
        {"filename": "test_pdf.pdf", "content": pdf_content}
    ]
    
    # Save files
    result = await real_s3_service.save_files_from_bytes(test_files, case_id)
    
    assert result["success"] is True
    assert len(result["s3_keys"]) == 2
    
    print(f"Saved files with S3 keys: {result['s3_keys']}")
    
    # Verify files exist in S3
    for s3_key in result["s3_keys"]:
        obj = real_s3_service.s3_client.head_object(
            Bucket=real_s3_service.aws_bucket_name,
            Key=s3_key
        )
        assert obj["ContentLength"] > 0
        print(f"File {s3_key} size: {obj['ContentLength']} bytes")
    
    # Cleanup
    for s3_key in result["s3_keys"]:
        real_s3_service.s3_client.delete_object(
            Bucket=real_s3_service.aws_bucket_name,
            Key=s3_key
        )

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_files_with_upload_file_objects(real_s3_service: FileService, test_environment):
    """Test save_files method with proper UploadFile objects"""
    case_id = "integration-test-case"
    
    # Read test file
    pdf_path = "test/test_data/case/file1.pdf"
    
    if not os.path.exists(pdf_path):
        pytest.skip("Test PDF file not found")
    
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    
    # Create proper UploadFile mock
    class MockUploadFile:
        def __init__(self, filename: str, content: bytes):
            self.filename = filename
            self.content_type = "application/pdf"
            self.size = len(content)
            self._file = io.BytesIO(content)
        
        async def read(self, size: int = -1):
            return self._file.read(size)
        
        async def seek(self, offset: int, whence: int = 0):
            return self._file.seek(offset, whence)
        
        def tell(self):
            return self._file.tell()
        
        def close(self):
            self._file.close()
    
    mock_files = [MockUploadFile("integration_test.pdf", pdf_content)]
    
    # Save files
    result = await real_s3_service.save_files(mock_files, case_id)
    
    assert result["success"] is True
    assert len(result["s3_keys"]) == 1
    
    s3_key = result["s3_keys"][0]
    print(f"Saved file with S3 key: {s3_key}")
    
    # Verify file exists
    obj = real_s3_service.s3_client.head_object(
        Bucket=real_s3_service.aws_bucket_name,
        Key=s3_key
    )
    assert obj["ContentLength"] > 0
    
    # Cleanup
    real_s3_service.s3_client.delete_object(
        Bucket=real_s3_service.aws_bucket_name,
        Key=s3_key
    )

@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_and_retrieve_response(real_s3_service: FileService, test_environment):
    """Test saving and retrieving JSON responses"""
    case_id = "integration-test-case"
    
    test_response = {
        "analysis": "Integration test analysis",
        "recommendations": ["Recommendation 1", "Recommendation 2"],
        "confidence": 0.95,
        "metadata": {
            "model": "test-model",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }
    
    # Save response
    result = await real_s3_service.save_respose_v2(test_response, case_id)
    
    assert result["success"] is True
    assert "s3_key" in result
    
    s3_key = result["s3_key"]
    print(f"Saved response with S3 key: {s3_key}")
    
    # Retrieve and verify content using extract_content
    retrieved_content = await real_s3_service.extract_content(s3_key)
    
    assert retrieved_content["analysis"] == test_response["analysis"]
    assert retrieved_content["confidence"] == test_response["confidence"]
    assert len(retrieved_content["recommendations"]) == 2
    assert retrieved_content["metadata"]["model"] == "test-model"
    
    # Cleanup
    real_s3_service.s3_client.delete_object(
        Bucket=real_s3_service.aws_bucket_name,
        Key=s3_key
    )

@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_text_extraction_and_caching(real_s3_service: FileService, test_environment):
    """Test PDF text extraction with caching functionality"""
    case_id = "integration-test-case"
    
    # Use actual test PDF
    pdf_path = "test/test_data/case/file1.pdf"
    
    if not os.path.exists(pdf_path):
        pytest.skip("Test PDF file not found")
    
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    
    # Upload PDF using save_files_from_bytes
    test_files = [{"filename": "test_extraction.pdf", "content": pdf_content}]
    upload_result = await real_s3_service.save_files_from_bytes(test_files, case_id)
    
    assert upload_result["success"] is True
    s3_key = upload_result["s3_keys"][0]
    
    print(f"Uploaded PDF with S3 key: {s3_key}")
    
    # Extract text (should cache automatically)
    extracted_text = await real_s3_service.extract_pdf_text_cached_from_s3(s3_key)
    
    assert len(extracted_text) > 0
    print(f"Extracted text length: {len(extracted_text)}")
    print(f"Extracted text preview: {extracted_text[:200]}...")
    
    # Test cache hit - should return same text quickly
    cached_text = await real_s3_service.extract_pdf_text_cached_from_s3(s3_key)
    assert cached_text == extracted_text
    
    # Verify cache was set
    cache_key = f"pdf:text:{s3_key}"
    cached_value = await real_s3_service.caching_service.get_str(cache_key)
    assert cached_value == extracted_text
    
    # Cleanup
    real_s3_service.s3_client.delete_object(
        Bucket=real_s3_service.aws_bucket_name,
        Key=s3_key
    )
    await real_s3_service.caching_service.delete(cache_key)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_text_from_multiple_files(real_s3_service: FileService, test_environment):
    """Test extracting text from multiple PDF files"""
    
    # Read multiple test PDFs
    pdf_paths = ["test/test_data/case/file1.pdf", "test/test_data/case/file2.pdf"]
    
    file_contents = []
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                file_contents.append({"content": f.read()})
    
    if not file_contents:
        pytest.skip("No test PDF files found")
    
    # Extract text from all files
    extracted_text = await real_s3_service.extract_text(file_contents)
    
    assert isinstance(extracted_text, str)
    assert len(extracted_text) > 0
    
    print(f"Extracted text from {len(file_contents)} files")
    print(f"Total extracted text length: {len(extracted_text)}")
    print(f"Text preview: {extracted_text[:300]}...")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_files_handling(real_s3_service: FileService, test_environment):
    """Test handling of empty files and edge cases"""
    case_id = "integration-test-case"
    
    # Test empty file list
    result = await real_s3_service.save_files_from_bytes([], case_id)
    assert result["success"] is True
    assert len(result["s3_keys"]) == 0
    
    # Test file with empty content
    empty_files = [{"filename": "empty.txt", "content": b""}]
    result = await real_s3_service.save_files_from_bytes(empty_files, case_id)
    # Should still succeed but might skip empty files
    assert result["success"] is True
    
    # Test file with no filename
    no_name_files = [{"filename": "", "content": b"Some content"}]
    result = await real_s3_service.save_files_from_bytes(no_name_files, case_id)
    # Should handle gracefully
    assert result["success"] is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_s3_error_handling(real_s3_service: FileService, test_environment):
    """Test error handling in S3 operations"""
    case_id = "integration-test-case"
    
    # Test extract_content with non-existent key
    non_existent_key = "non-existent/key.json"
    result = await real_s3_service.extract_content(non_existent_key)
    assert "error" in result
    
    # Test PDF extraction with non-existent key
    extracted_text = await real_s3_service.extract_pdf_text_cached_from_s3(non_existent_key)
    assert extracted_text == ""  # Should return empty string on error
    
    print("Error handling tests passed")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_s3_key_generation_patterns(real_s3_service: FileService, test_environment):
    """Test S3 key generation for different file types"""
    case_id = "test-case-123"
    
    # Test text file
    text_result = await real_s3_service.create_text_file_and_save("Test content", case_id)
    assert text_result["success"] is True
    text_key = text_result["s3_key"]
    assert text_key.startswith(f"{case_id}/text_input")
    assert text_key.endswith(".txt")
    
    # Test response file
    response_result = await real_s3_service.save_respose_v2({"test": "data"}, case_id)
    assert response_result["success"] is True
    response_key = response_result["s3_key"]
    assert response_key.startswith(f"{case_id}/response_")
    assert response_key.endswith(".json")
    
    print(f"Text file key: {text_key}")
    print(f"Response file key: {response_key}")
    
    # Cleanup
    for key in [text_key, response_key]:
        real_s3_service.s3_client.delete_object(
            Bucket=real_s3_service.aws_bucket_name,
            Key=key
        )