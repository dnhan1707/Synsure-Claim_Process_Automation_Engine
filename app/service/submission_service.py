from app.service.supabase_service import SupabaseServiceV2
from app.service.model_service import ModelService
from app.service.case_service_v2 import CaseService
from app.service.s3_service_v2 import S3Service
from app.service.model_service import ModelService
from fastapi import UploadFile
import uuid
import logging
import asyncio


logger = logging.getLogger(__name__)

class SubmissionService:
    def __init__(self):
        self.sp_service = SupabaseServiceV2()
        self.s3_service = S3Service()
        self.case_service = CaseService()
        self.model_response = ModelService()

    async def submit_new_case(
        self,
        tenant_id: str, 
        case_name: str, 
        files: list[UploadFile]    
    ) -> tuple: # (new_case_id, model_response)
        try:
            file_contents = []
            for file in files:
                content = await file.read()
                file_contents.append({"filename": file.filename, "content": content})

            model_service = ModelService()
            model_response = await model_service.generate_response_v2(
                file_contents=file_contents
            )

            if not isinstance(model_response, dict):
                logger.error("Error model_response is not dict")
                return {}
            
            new_case_id, saved_files_id = await self.case_service.create_new_case(tenant_id, case_name, files)
            
            # save into s3
            new_response_file_id = str(uuid.uuid4())
            response_file_key = await self.s3_service.save_response_json(tenant_id, new_case_id, new_response_file_id, model_response)
            if not response_file_key:
                logger.error("Error save_response_json in submit_new_case")
                return ("", {})

            # save into responses table
            response_row = await self.sp_service.insert_one(
                table_name="responses",
                object={
                    "id": new_response_file_id,
                    "tenant_id": tenant_id,
                    "case_id": new_case_id,
                    "s3_key": response_file_key
                }
            )

            # save into response_input_files table
            rows = []
            for fid in saved_files_id:
                rows.append({
                    "file_id": fid,
                    "response_id": new_response_file_id
                })
            
            insert_bulk_response = await self.sp_service.insert_bulk(
                table_name="response_input_files",
                list_object=rows
            )
            if not insert_bulk_response:
                logger.error("Error insert_bulk in submit_new_case")
                return ("", {})


            return (new_case_id, model_response)
        
        except Exception as e:
            logger.error("Error submit_new_case")
            return ("", {})
    

    async def submit_with_chosen_files(
        self,
        tenant_id: str,
        case_id: str,
        chosen_files: list[str]  # list of file IDs
    ) -> dict:
        try:
            read_data = []

            async def _process_file(file_id: str):
                file_data = await self.sp_service.get_by_id(
                    table_name="files",
                    columns="name, s3_key",
                    id=file_id
                )
                if not file_data:
                    logger.warning(f"File not found for id={file_id}")
                    return None

                s3_key = file_data["s3_key"]
                raw_content = await self.s3_service.get_file_raw_bytes(s3_key)
                return {
                    "filename": file_data["name"],
                    "content": raw_content
                }

            # process all files concurrently
            results = await asyncio.gather(*[_process_file(fid) for fid in chosen_files])
            read_data = [r for r in results if r]

            if not read_data:
                logger.error("No valid files found in submit_with_chosen_files")
                return {}

            # Generate model response
            model_response = await self.model_response.generate_response_v2(read_data)

            # Save into S3
            new_response_file_id = str(uuid.uuid4())
            response_file_key = await self.s3_service.save_response_json(
                tenant_id, case_id, new_response_file_id, model_response
            )
            if not response_file_key:
                logger.error("Error save_response_json in submit_with_chosen_files")
                return {}
            
            # Save into responses table
            await self.sp_service.insert_one(
                table_name="responses",
                object={
                    "id": new_response_file_id,
                    "tenant_id": tenant_id,
                    "case_id": case_id,
                    "s3_key": response_file_key
                }
            )

            # Save into response_input_files table
            rows = [{"file_id": fid, "response_id": new_response_file_id} for fid in chosen_files]
            await self.sp_service.insert_bulk("response_input_files", rows)

            return model_response

        except Exception as e:
            logger.error(f"Error submit_with_chosen_files: {e}")
            return {}
