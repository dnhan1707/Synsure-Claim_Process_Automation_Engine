from app.celery_app import celery_app
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

        s3_text_result = await self.file_service.create_text_file_and_save(content=manual_inputs)
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

        files_keys_result = await self.file_service.save_files(files=files)
        files_keys = files_keys_result.get("s3_keys") if isinstance(files_keys_result, dict) else []
        return [
            {
                "case_id": case_id,
                "case_name": case_name,
                "s3_link": s3_key,
                "response_id": response_data_id
            }
            for s3_key in files_keys
        ]
    

    async def save_manual_and_files(
        self,
        case_id: str,
        case_name: str,
        manual_inputs: str,
        files: Optional[List[UploadFile]],
        response_data_id: Optional[str],
        file_contents: Optional[List[Dict[str, Any]]] = None
    ):
        
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


    async def save_uploaded_files_from_contents(
            self,
            file_contents: List[Dict[str, Any]],
            case_id: str,
            case_name: str,
            response_data_id: Optional[str],
        ) -> List[dict]:
            """
            Uses already-read bytes to upload to S3 (no re-read of UploadFile).
            """
            files_keys_result = await self.file_service.save_files_from_bytes(items=file_contents)
            files_keys = files_keys_result.get("s3_keys") if isinstance(files_keys_result, dict) else []
            return [
                {
                    "case_id": case_id,
                    "case_name": case_name,
                    "s3_link": s3_key,
                    "response_id": response_data_id,
                }
                for s3_key in files_keys
            ]
    

    async def proceed_with_model(
            self, 
            case_id: str, 
            case_name: str, 
            manual_input: str, 
            files: Optional[List[UploadFile]]
        ):
        
        # Read each file once
        file_contents: List[Dict[str, Any]] = []
        if files:
            for file in files:
                content = await file.read()
                file_contents.append({"filename": file.filename, "content": content})

        # Generate model response using the bytes we already read
        response = await self.model_service.generate_response_v2(
            file_contents=file_contents,
            manual_input=manual_input or ""
        )

        # Save response JSON to S3
        response_saved_res = await self.file_service.save_respose_v2(response=response)
        response_s3_key = response_saved_res.get("s3_key") if isinstance(response_saved_res, dict) else None

        # Save response row
        response_row = await self.sp_service.insert(
            table_name="response",
            object={"case_id": case_id, "s3_link": response_s3_key}
        )
        response_data_id = response_row["id"] if response_row and "id" in response_row else None

        # Save manual and files without re-reading uploads
        await self.save_manual_and_files(
            case_id=case_id,
            case_name=case_name,
            manual_inputs=manual_input,
            files=None,  # avoid re-reading UploadFile
            response_data_id=response_data_id,
            file_contents=file_contents,  # reuse bytes for upload
        )

        return response


    async def proceed_with_model_history_files(self, case_id: str):
        # Get file metadata from Supabase
        files_metadata = await self.sp_service.get_files_by_case_id(case_id)

        # Aggregate cached PDF text + manual input text (from prior saved .txt)
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

            elif filename.startswith("texts_") and filename.endswith(".txt"):
                # Load manual input text once
                s3_obj = self.file_service.s3_client.get_object(
                    Bucket=self.file_service.aws_bucket_name,
                    Key=s3_link
                )
                manual_input = s3_obj["Body"].read().decode("utf-8")

        aggregated_details = "".join(details_parts)

        # Generate model response without re-parsing PDFs
        response = await self.model_service.generate_response_v2(
            file_contents=[],  # nothing to parse
            manual_input=f"{manual_input}{aggregated_details}"
        )

        # Save response to S3
        response_saved_res = await self.file_service.save_respose_v2(response=response)
        response_s3_key = response_saved_res.get("s3_key") if isinstance(response_saved_res, dict) else None

        # Save response to Supabase
        response_row = await self.sp_service.insert(
            table_name="response",
            object={
                "case_id": case_id,
                "s3_link": response_s3_key
            }
        )
        response_data_id = response_row["id"] if response_row and "id" in response_row else None

        # Link existing files to this response (use Supabase metadata only)
        files_to_insert = []
        for file in files_metadata:
            files_to_insert.append({
                "case_id": case_id,
                "case_name": file.get("case_name"),
                "s3_link": file.get("s3_link"),
                "response_id": response_data_id
            })
        if files_to_insert:
            await self.sp_service.insert_bulk(table_name="files", objects=files_to_insert)

        return response

