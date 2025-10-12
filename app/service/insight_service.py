from app.service.supabase_service import SupabaseServiceV2
import logging

logger = logging.getLogger(__name__)

class InsightService:
    def __init__(self):
        self.sp_service = SupabaseServiceV2()

    async def get_most_case_type_by_tenant(self, tenant_id: str) -> str:
        try:
            response = await self.sp_service.get_by_tenant_id(
                table_name="cases", 
                tenant_id=tenant_id, 
                column="case_type"
            )
            
            if not response:
                return ""
            
            from collections import Counter
            
            case_types = [
                record["case_type"] 
                for record in response 
                if record.get("case_type")  
            ]
            
            if not case_types:
                return ""
            
            counter = Counter(case_types)
            most_common = counter.most_common(1)
            
            return most_common[0][0] if most_common else ""

        except Exception as e:
            logger.error(f"Error get_most_case_type_by_tenant: {e}", exc_info=True)
            return ""


    async def get_most_case_type_general(self) -> str:
        try:
            response = await self.sp_service.get_from_cases_table(
                column="case_type"
            )
            
            if not response:
                return ""
            
            from collections import Counter
            
            case_types = [
                record["case_type"] 
                for record in response 
                if record.get("case_type")  
            ]
            
            if not case_types:
                return ""
            
            counter = Counter(case_types)
            most_common = counter.most_common(1)
            
            return most_common[0][0] if most_common else ""

        except Exception as e:
            logger.error(f"Error get_most_case_type_general: {e}", exc_info=True)
            return ""


    async def get_all_type_general(self) -> list[str]:
        try:
            response = await self.sp_service.get_from_cases_table(
                column="case_type"
            )

            if not response:
                return []
            
            unique_val = set()
            case_types = []

            for record in response:
                case_type = record.get("case_type")
                if case_type is not None and case_type not in unique_val:
                    case_types.append(case_type)
                    unique_val.add(case_type)

            return case_types

        except Exception as e:
            logger.error(f"Error get_all_type_by_tenant in InsightService: {e}", exc_info=True)
            return []


    async def get_all_type_by_tenant(self, tenant_id: str) -> list[str]:
        try:
            response = await self.sp_service.get_by_tenant_id(
                table_name="cases",
                tenant_id=tenant_id,
                column="case_type"
            )

            if not response:
                return []
            
            unique_val = set()
            case_types = []

            for record in response:
                case_type = record.get("case_type")
                if case_type is not None and case_type not in unique_val:
                    case_types.append(case_type)
                    unique_val.add(case_type)

            return case_types

        except Exception as e:
            logger.error(f"Error get_all_type_by_tenant in InsightService: {e}", exc_info=True)
            return ""

