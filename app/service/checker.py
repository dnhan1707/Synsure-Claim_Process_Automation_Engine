from app.service.supabase_service import SupabaseService
from fastapi import UploadFile
import logging
import uuid

logger = logging.getLogger(__name__)

class Checker:
    def __init__(self):
        self.sp_service = SupabaseService()

    async def file_duplicate(
        self,
        tenant_id: str,
        case_id: str,
        files: list[UploadFile]
    ) -> dict[str, any]:
        
        try:
            logger.info("Checking for file duplicates by name in case %s", case_id)
            
            if not files:
                logger.warning("No files were uploaded")
                return {
                    "success": True,
                    "has_duplicates": False,
                    "proceed_token": None,
                    "duplicates": [],
                    "new_files": []
                }

            # Find existing files
            existed_files = await self.sp_service.get_all_files(
                table_name="files",
                case_id=case_id,
                tenant_id=tenant_id,
                columns="id, name, s3_key, s3_bucket, uploaded_at" 
            )

            if not existed_files:
                logger.info("This case has no files yet")
                # All files are new
                new_files = [{"filename": file.filename, "size": None} for file in files]
                return {
                    "success": True,
                    "has_duplicates": False,
                    "proceed_token": None,
                    "duplicates": [],
                    "new_files": new_files
                }
            
            logger.info("Found %d existing files in case", len(existed_files))
            
            # Create lookup table
            existing_by_name = {}
            for existing_file in existed_files:
                file_name = existing_file["name"]
                existing_by_name[file_name] = existing_file
            
            duplicates = []
            new_files = []
            has_dup = False

            for file in files:
                filename = file.filename

                if filename in existing_by_name:
                    existing_file = existing_by_name[filename] 
                    duplicates.append({
                        "filename": filename,
                        "size": None,
                        "existing_file": {
                            "id": existing_file["id"],
                            "filename": existing_file["name"],
                            "size": None,
                            "uploaded_at": existing_file["uploaded_at"]
                        },
                        "match_type": "name_only"  
                    })
                    has_dup = True
                    logger.info("Found duplicate filename: %s", filename)
                else:
                    # New file
                    new_files.append({
                        "filename": filename,
                        "size": None
                    })
                    logger.info("New file: %s", filename)

            # Generate proceed token if duplicates found
            proceed_token = None
            if has_dup:
                proceed_token = str(uuid.uuid4())
                logger.info("Generated proceed token for %d duplicates", len(duplicates))

            result = {
                "success": True,
                "has_duplicates": has_dup,  
                "proceed_token": proceed_token,
                "duplicates": duplicates,
                "new_files": new_files
            }
            
            logger.info("Duplicate check complete: %d duplicates, %d new files", 
                       len(duplicates), len(new_files))
            
            return result
    
        except Exception as e:
            logger.error("Error in file_duplicate: %s", str(e), exc_info=True)  
            return {
                "success": False,  
                "error": str(e),
                "has_duplicates": False,
                "proceed_token": None,
                "duplicates": [],
                "new_files": []
            }