from app.service.supabase_service import SupabaseServiceV2
import logging

logger = logging.getLogger(__name__)

class DashboardService:
    def __init__(self):
        self.sp_service = SupabaseServiceV2()

    async def get_cases_not_processed(self) -> dict:
        try:
            res = await self.sp_service.get_case_with_status(
                column="id, status, case_name, case_type, short_des",
                status="open"
            )

            return {"count": len(res), "data": res}

        except Exception as e:
            logger.error("Error in: get_cases_not_processed")
            return {}
