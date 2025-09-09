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
            return False


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

