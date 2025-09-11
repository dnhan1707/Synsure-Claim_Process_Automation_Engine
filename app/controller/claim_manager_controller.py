import logging
from fastapi import UploadFile, File
from typing import List, Dict, Any
from app.service.claim_manager_service import ClaimManagerService

logger = logging.getLogger(__name__)

class ClaimManagerController:
    def __init__(self):
        self.claim_manager_service = ClaimManagerService()

    async def create_new_claim(
        self,
        tenant_id: str,
        case_name: str,
        files: List[UploadFile] = File(None)
    ) -> bool:

        try:
            res = None

            if not files:
                res = await self.claim_manager_service.create_empty_claim(
                    tenant_id=tenant_id,
                    name=case_name
                )

            elif files:
                res = await self.claim_manager_service.create_claim(
                    tenant_id=tenant_id,
                    name=case_name,
                    files=files
                )

            if not res:
                logger.warning("Failed to create claim for tenant_id: %s, case_name: %s", tenant_id, case_name)

            return res
        except Exception as e:
            logger.error("Error in create_new_claim for tenant_id: %s, case_name: %s - %s", tenant_id, case_name, str(e), exc_info=True)
            return False
        

    async def get_claim_by_id(self, id: str) -> Dict[str, Any]:
        try:
            res = await self.claim_manager_service.get_claim_by_id(id)
            if not res:
                logger.error("Error in get_claim_by_id, either None or crash")
                return {}

            return res

        except Exception as e:
            logger.error("Error in get_claim_by_id for id: %s, case_name: %s - %s", id, str(e), exc_info=True)
            return {}


    async def get_all_claim(self) -> List[Dict[str, Any]]:
        try:
            res = await self.claim_manager_service.get_all_claim()
            if not res:
                logger.error("Error in get_all_claim, either None or crash")
                return []

            return res

        except Exception as e:
            logger.error("Error in get_all_claim", str(e), exc_info=True)
            return []


    async def update_claim_name(self, id: str, new_name: str) -> bool:
        try:
            res = await self.claim_manager_service.update_claim_name(id, new_name)

            if not res:
                return False
            
            return True
        
        except Exception as e:
            logger.error("Error in update_claim_name: ", str(e), exc_info=True)
            return False


    async def upload_files_existed_case(self, tenant_id: str, case_id: str, files: List[UploadFile]) -> bool:
        try:
            res = await self.claim_manager_service.upload_files_existed_case(tenant_id, case_id, files)

            if not res:
                return False
            
            return True

        except Exception as e:
            logger.error("Error in update_claim_name: ", str(e), exc_info=True)
            return False

    async def replace_existed_file(self, tenant_id: str, case_id: str, file_id: str, new_file: UploadFile) -> bool:
        try:
            res = await self.claim_manager_service.replace_existed_file(tenant_id, case_id, file_id, new_file)

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
            
            res = await self.claim_manager_service.remove_files(file_ids)
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
            
            res = await self.claim_manager_service.remove_case(case_id)
            if not res:
                logger.warning("Failed to remove case: %s", case_id)
                return False
            
            logger.info("Successfully removed case: %s", case_id)
            return True
            
        except Exception as e:
            logger.error("Error in remove_case for case_id: %s - %s", case_id, str(e), exc_info=True)
            return False
