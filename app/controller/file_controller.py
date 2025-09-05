from typing import List, Dict, Any
from app.service.supabase_service import SupabaseService
from app.service.s3_service import FileService


class FileController:
    def __init__(self):
        self.sp_service = SupabaseService()
        self.file_service = FileService()


    async def get_case_files_links_supabase(self, case_id: str) -> List[Dict[str, Any]]:
        try:
            files = await self.sp_service.get_files_by_case_id(case_id)
            result = []
            for file in files:
                s3_key = file.get("s3_link", "")
                file_id = file.get("id", "")
                filename = s3_key.split("/")[-1]
                url = self.file_service.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.file_service.aws_bucket_name, 'Key': s3_key},
                    ExpiresIn=3600
                )
                file_type = "pdf" if filename.lower().endswith(".pdf") else "text" if filename.lower().endswith(".txt") else "other"
                result.append({
                    "filename": filename,
                    "url": url,
                    "type": file_type,
                    "id": file_id
                })

            responses = await self.sp_service.get_responses_by_case_id(case_id)
            for resp in responses:
                s3_key = resp.get("s3_link", "")
                response_file_id = resp.get("id", "")
                filename = s3_key.split("/")[-1]
                url = self.file_service.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.file_service.aws_bucket_name, 'Key': s3_key},
                    ExpiresIn=3600
                )
                file_type = "response_json" if filename.lower().endswith(".json") else "other"
                result.append({
                    "filename": filename,
                    "url": url,
                    "type": file_type,
                    "id": response_file_id
                })

            return result
        except Exception as e:
            return []
        

    async def remove_files(self, file_id: str) -> bool:
        """Set file record as inactive"""
        try:
            result = await self.sp_service.update(
                table_name="files",
                id=file_id,
                objects={"is_active": False}
            )
            return result is not None
        except Exception as e:
            print(f"Error removing file {file_id}: {e}")
            return False

    async def remove_response(self, file_id: str) -> bool:
        """Set response record as inactive"""
        try:
            result = await self.sp_service.update(
                table_name="response",
                id=file_id,
                objects={"is_active": False}
            )
            return result is not None
        except Exception as e:
            print(f"Error removing response {file_id}: {e}")
            return False