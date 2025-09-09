import logging
from fastapi import UploadFile, File, Form
from typing import List
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