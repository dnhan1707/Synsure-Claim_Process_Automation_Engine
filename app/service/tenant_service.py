import logging
from app.service.supabase_service import SupabaseService
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TenantService():
    def __init__(self):
        self.sp_service = SupabaseService()
        self.table_name = "tenants"

    async def insert_new_tenant(self, name: str) -> bool:
        try:
            insert_res = await self.sp_service.insert(
                table_name=self.table_name,
                object={
                    "name": name
                }
            )

            if not insert_res: 
                logger.warning("Failed to insert tenant with name: %s", name)
                return False

            logger.info("Successfully created tenant with name: %s", name)
            return True

        except Exception as e:
            logger.error("Tenant Service Error - insert_new_tenant for name: %s - %s", name, str(e), exc_info=True)
            return False
        
    async def get_all_tenants(self) -> List[Dict[str, Any]]:
        try:
            res = await self.sp_service.get_all(
                table_name=self.table_name,
                columns="id, name"
            )

            if not res:
                logger.info("No tenants found")
                return []

            logger.info("Retrieved %d tenants", len(res))
            return res

        except Exception as e:
            logger.error("Tenant Service Error - get_all_tenants - %s", str(e), exc_info=True)
            return []
        
    
    async def get_tenant(self, id: str) -> Dict[str, Any]:
        try:
            res = await self.sp_service.get_row_by_id(
                id=id,
                table_name=self.table_name,
                columns="name"
            )

            if not res:
                logger.warning("Tenant not found with id: %s", id)
                return {}

            logger.info("Successfully retrieved tenant with id: %s", id)
            return res

        except Exception as e:
            logger.error("Tenant Service Error - get_tenant for id: %s - %s", id, str(e), exc_info=True)
            return {}