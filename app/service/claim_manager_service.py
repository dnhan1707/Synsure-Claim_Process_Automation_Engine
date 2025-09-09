import logging
from app.service.supabase_service import SupabaseService
from app.schema.schema import CaseStatus

logger = logging.getLogger(__name__)

class ClaimManagerService:
    def __init__(self):
        self.sp_service = SupabaseService()

    async def create_empty_claim(self, tenant_id: str, name: str, status: CaseStatus = CaseStatus.open) -> bool:
        try:
            res = await self.sp_service.insert(
                table_name="cases",
                object={
                    "tenant_id": tenant_id,
                    "status": status.value,
                    "case_name": name
                }
            )

            if not res:
                logger.warning("Failed to insert case for tenant_id: %s, case_name: %s", tenant_id, name)
                return False
            
            logger.info("Successfully created empty claim for tenant_id: %s, case_name: %s", tenant_id, name)
            return True

        except Exception as e:
            logger.error("Claim Manager Service Error - create_empty_claim for tenant_id: %s, case_name: %s - %s", 
                        tenant_id, name, str(e), exc_info=True)
            return False