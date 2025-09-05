from app.service.supabase_service import SupabaseService
from app.service.s3_service import FileService
from app.service.model_service import ModelService
from typing import List, Optional, Dict, Any
from fastapi import UploadFile


class CaseService:
    def __init__(self):
        self.sp_service = SupabaseService()
        self.file_service = FileService()
        self.model_service = ModelService()

        
    async def save_manual_input(
        self, 
        manual_inputs: str, 
        case_id: str, 
        case_name: str, 
        response_data_id: Optional[str]
    ) -> Optional[dict]:

        s3_text_result = await self.file_service.create_text_file_and_save(content=manual_inputs, case_id=case_id)
        text_s3_key = s3_text_result.get("s3_key") if isinstance(s3_text_result, dict) else None
        if text_s3_key:
            return {
                "case_id": case_id,
                "case_name": case_name,
                "s3_link": text_s3_key,
                "response_id": response_data_id
            }
        return None


    async def save_uploaded_files(
        self,
        files: List[UploadFile],
        case_id: str,
        case_name: str,
        response_data_id: Optional[str]
    ) -> List[dict]:
        result = await self.file_service.save_files(files=files, case_id=case_id)
        
        # Add proper null/error checking
        if not isinstance(result, dict) or "s3_keys" not in result:
            return []
        
        s3_keys = result.get("s3_keys")
        if not s3_keys:  
            return []
        
        files_metadata = []
        for s3_key in s3_keys:
            files_metadata.append({
                "case_id": case_id,
                "case_name": case_name,
                "s3_link": s3_key,
                "response_id": response_data_id
            })
        
        return files_metadata
    
    
    async def save_uploaded_files_from_contents(
        self,
        file_contents: List[Dict[str, Any]],
        case_id: str,
        case_name: str,
        response_data_id: Optional[str],
    ) -> List[dict]:
        result = await self.file_service.save_files_from_bytes(items=file_contents, case_id=case_id)
        
        # Add proper null/error checking
        if not isinstance(result, dict) or "s3_keys" not in result:
            return []
        
        s3_keys = result.get("s3_keys")
        if not s3_keys:  
            return []
        
        files_metadata = []
        for s3_key in s3_keys:
            files_metadata.append({
                "case_id": case_id,
                "case_name": case_name,
                "s3_link": s3_key,
                "response_id": response_data_id
            })
        
        return files_metadata


    async def save_manual_and_files(
        self,
        case_id: str,
        case_name: str,
        manual_inputs: str,
        files: Optional[List[UploadFile]],
        response_data_id: Optional[str],
        file_contents: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        
        files_to_insert = []

        # Save manual input if provided
        if manual_inputs:
            text_file = await self.save_manual_input(manual_inputs, case_id, case_name, response_data_id)
            if text_file:
                files_to_insert.append(text_file)

        # Save files using bytes if provided; else fall back to UploadFile flow
        if file_contents:
            uploaded_files = await self.save_uploaded_files_from_contents(file_contents, case_id, case_name, response_data_id)
            files_to_insert.extend(uploaded_files)
        elif files:
            uploaded_files = await self.save_uploaded_files(files, case_id, case_name, response_data_id)
            files_to_insert.extend(uploaded_files)

        # Bulk insert new files
        if files_to_insert:
            await self.sp_service.insert_bulk(table_name="files", objects=files_to_insert)
    

    async def proceed_with_model(self, case_id: str, case_name: str, manual_input: str, files: Optional[List[UploadFile]]):
        # Now much simpler and testable
        file_contents = await self._read_uploaded_files(files) if files else []
        response = await self.model_service.generate_response_v2(file_contents, manual_input or "")
        response_data_id = await self._save_model_response(response, case_id)
        
        await self.save_manual_and_files(
            case_id=case_id, case_name=case_name, manual_inputs=manual_input,
            files=None, response_data_id=response_data_id, file_contents=file_contents
        )
        return response
    

    async def proceed_with_model_history_files(self, case_id: str):
        """
        Generate model response using previously uploaded files for a case.
        Uses cached PDF text and aggregates with manual input.
        """
        # Get file metadata from Supabase
        files_metadata = await self.sp_service.get_files_by_case_id(case_id)
        
        # Aggregate content from existing files
        manual_input, aggregated_details = await self._aggregate_file_contents_from_metadata(files_metadata)
        
        # Generate model response using aggregated content
        combined_input = f"{manual_input}{aggregated_details}"
        response = await self.model_service.generate_response_v2(
            file_contents=[],  # No new files to parse
            manual_input=combined_input
        )
        
        # Save the response
        response_data_id = await self._save_model_response(response, case_id)
        
        # Link existing files to this new response
        if response_data_id:
            await self._link_existing_files_to_response(files_metadata, case_id, response_data_id)
        
        return response


# -------------------------------------------------------------Helper Function------------------------------------------------------------------

    async def _read_uploaded_files(self, files: List[UploadFile]) -> List[Dict[str, Any]]:
        """Extract this for easier testing"""
        file_contents = []
        for file in files:
            content = await file.read()
            file_contents.append({"filename": file.filename, "content": content})
        return file_contents
        

    async def _save_model_response(self, response: dict, case_id: str) -> Optional[str]:
        """Extract this for easier testing"""
        response_saved_res = await self.file_service.save_respose_v2(response=response, case_id=case_id)
        response_s3_key = response_saved_res.get("s3_key") if isinstance(response_saved_res, dict) else None
        
        response_row = await self.sp_service.insert(
            table_name="response",
            object={"case_id": case_id, "s3_link": response_s3_key}
        )
        return response_row.get("id") if response_row else None


    async def _aggregate_file_contents_from_metadata(self, files_metadata: List[Dict]) -> tuple[str, str]:
        """
        Extract and aggregate content from files based on metadata.
        Returns: (manual_input, aggregated_pdf_text)
        """
        details_parts = []
        manual_input = ""

        for file in files_metadata:
            s3_link = file.get("s3_link", "")
            filename = s3_link.split("/")[-1].lower()

            if filename.endswith(".pdf"):
                # Use Redis-cached extraction by S3 key
                text = await self.file_service.extract_pdf_text_cached_from_s3(s3_link)
                if text:
                    details_parts.append(text)

            elif filename.endswith(".txt"):
                # Load manual input text
                manual_input = await self._load_text_from_s3(s3_link)

        aggregated_details = "".join(details_parts)
        return manual_input, aggregated_details


    async def _load_text_from_s3(self, s3_key: str) -> str:
        """Load text content from S3 key."""
        try:
            s3_obj = self.file_service.s3_client.get_object(
                Bucket=self.file_service.aws_bucket_name,
                Key=s3_key
            )
            return s3_obj["Body"].read().decode("utf-8")
        except Exception:
            return ""


    async def _link_existing_files_to_response(self, files_metadata: List[Dict], case_id: str, response_data_id: str) -> None:
        """Link existing files to a new response by updating their response_id."""
        for file_metadata in files_metadata:
            file_id = file_metadata.get("id")
            if file_id:
                # Update existing file record to link to new response
                await self.sp_service.update(
                    table_name="files",
                    id=file_id,
                    objects={"response_id": response_data_id}
                )
