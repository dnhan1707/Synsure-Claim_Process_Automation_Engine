from app.service.supabase_service import SupabaseService
from typing import Dict, Any, List


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
                return False

            return True

        except Exception as e:
            print("Tenant Service Error - insert_new_tenant: ", e)
            return False
        
    async def get_all_tenants(self) -> List[Dict[str, Any]]:
        try:
            res = await self.sp_service.get_all(
                table_name=self.table_name,
                columns="id, name"
            )

            if not res:
                return []

            return res

        except Exception as e:
            print("Tenant Service Error - get_all_tenants: ", e)
            return []
        
    
    async def get_tenant(self, id: str) -> Dict[str, Any]:
        try:
            res = await self.sp_service.get_row_by_id(
                id=id,
                table_name=self.table_name,
                columns="name"
            )

            if not res:
                return {}

            return res

        except Exception as e:
            print("Tenant Service Error - get_tenant: ", e)
            return {}
        