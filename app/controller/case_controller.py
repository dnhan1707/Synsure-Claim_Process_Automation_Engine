from fastapi import UploadFile
from typing import List, Optional, Dict, Any
from app.service.supabase_service import SupabaseService
from app.service.s3_service import FileService
from app.service.case_service import CaseService
import logging

logger = logging.getLogger(__name__)

# This controller include the logic of the route
class CaseControllerV2():
    def __init__(self):
        self.sp_service = SupabaseService()
        self.case_service = CaseService()
        self.file_service =  FileService()


    async def get_latest_response(self, case_id: str) -> Dict[str, Any]:
        try:
            latest_response = await self.sp_service.get_latest_response_by_case_id(case_id)
            if not latest_response or not latest_response.get("s3_link"):
                return {"success": False, "error": "No response found"}

            s3_key = latest_response["s3_link"]
            content = await self.file_service.extract_content(s3_key)
            return content

        except Exception as e:
            return {"success": False, "error": str(e)}


    async def submit_one_case(
        self,
        case_id: Optional[str],
        case_name: Optional[str],
        manual_input: Optional[str],
        files: Optional[List[UploadFile]]
    ) -> Dict[str, Any]:
        try:
            '''
            if no case_id -> this is new case:
                respose = proceed with model
                    - extract text from pdf
                    - combine with manual text
                    - create prompt
                    - generate response with validator:
                        if valid -> return
                        if not retry

                save into s3:
                    - update response table with its s3_link
                    - extract id
                    - save new files into s3
                    - update files table with response_id
                        
            else this is existed case:
                if having new input or new files, 
                    proceed with model
                else:
                    proceed with history files
            '''
            if not case_id or case_id == "":
                # create a case
                case_row = await self.sp_service.insert(table_name="case", object={"case_name": case_name})
                case_id = case_row["id"] if case_row and "id" in case_row else None
                result = await self.case_service.proceed_with_model(case_id, case_name, manual_input, files)
                return result, case_id
            
            else:
                if manual_input or files:
                    result = await self.case_service.proceed_with_model(case_id, case_name, manual_input, files)
                    return result, case_id
            
                else:
                    result = await self.case_service.proceed_with_model_history_files(case_id)
                    return result, case_id


        except Exception as e:
            return {"success": False, "error submit one case function": str(e)}

    async def submit_bulk(self, case_ids: List[str]) -> Dict[str, Any]:
        try:
            for id in case_ids:
                await self.case_service.proceed_with_model_history_files(id)
            
            return {"success": True}
        
        except Exception as e:
            return {"success": False, "error": str(e)}


class CaseControllerV3():
    def __init__(self):
        self.sp_service = SupabaseService()
        self.case_service = CaseService()

    async def get_all_cases(self, tenant_id: str) -> List[Dict[str, Any]]:
        try:
            res = await self.sp_service.get_all_claim_by_tenant_id(
                table_name="cases",
                tenant_id=tenant_id,
                columns="id, case_name, status"
            )
            if not res:
                logger.warning("Empty or crash in CaseControllerV3 get_all_cases")
                return []
            
            return res

        except Exception as e:
            logger.error("Error in CaseControllerV3 get_all_cases")
            return []


    async def get_case(self, tenant_id: str, case_id: str) -> Dict[str, Any]:
        try:
            res = await self.case_service.get_case(tenant_id, case_id)
            if not res:
                logger.error("Error in get_claim_by_id, either None or crash")
                return {}

            return res

        except Exception as e:
            return {}


    async def create_new_case(
            self,
            tenant_id: str, 
            case_name: str,  
            files: Optional[List[UploadFile]]
        ) -> bool:
        try:
            res = await self.case_service.create_new_case(tenant_id, case_name, files)
            return res
        except Exception as e:
            return False
    

    async def upload_files_existed_case(
            self,
            tenant_id: str, 
            case_name: str,  
            files: List[UploadFile]
        ) -> bool:
        try:
            res = await self.case_service.upload_files_existed_case(tenant_id, case_name, files)
            return res
        except Exception as e:
            return False
        

    async def update_claim_name(self, case_id: str, new_name: str) -> bool:
        try:
            res = await self.case_service.update_claim_name(case_id, new_name)

            if not res:
                return False
            
            return True
        
        except Exception as e:
            logger.error("Error in update_claim_name: ", str(e), exc_info=True)
            return False

    async def remove_files(self, file_ids: List[str]) -> bool:
        """
        Remove multiple files by their IDs
        """
        try:
            logger.info("Controller: Removing %d files", len(file_ids))
            
            res = await self.case_service.remove_files(file_ids)
            if not res:
                logger.warning("Failed to remove files: %s", file_ids)
                return False
            
            logger.info("Successfully removed files: %s", file_ids)
            return True
            
        except Exception as e:
            logger.error("Error in remove_files for file_ids: %s - %s", file_ids, str(e), exc_info=True)
            return False

    async def remove_case(self, case_id: str) -> bool:
        """
        Remove a case and all its associated files
        """
        try:
            logger.info("Controller: Removing case %s", case_id)
            
            res = await self.case_service.remove_case(case_id)
            if not res:
                logger.warning("Failed to remove case: %s", case_id)
                return False
            
            logger.info("Successfully removed case: %s", case_id)
            return True
            
        except Exception as e:
            logger.error("Error in remove_case for case_id: %s - %s", case_id, str(e), exc_info=True)
            return False
