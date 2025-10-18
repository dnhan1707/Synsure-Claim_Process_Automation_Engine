from app.service.supabase_service import SupabaseServiceV2
import logging
from datetime import datetime, timedelta
from collections import Counter
from typing import Optional, Dict, List, Any

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


    async def get_insights(self, date: str = None, tenant_id: str = None) -> Dict[str, Any]:
            """
            Get comprehensive insights with optional date and tenant filtering.
            
            Args:
                date: Optional date filter in YYYY-MM-DD format (filters for that specific day)
                tenant_id: Optional tenant filter
                
            Returns:
                {
                    "date": "2025-01-16" or None,
                    "tenant_id": "tenant-123" or None,
                    "total_cases": 150,
                    "summary": {
                        "total_accepted": 45,
                        "total_rejected": 30,
                        "total_review_required": 75,
                        "acceptance_rate": 30.0,
                        "rejection_rate": 20.0,
                        "review_rate": 50.0
                    },
                    "data": [
                        {
                            "type": "auto",
                            "total_cases": 50,
                            "accepted": 15,
                            "rejected": 10,
                            "review_required": 25,
                            "percent_accepted": 30.0,
                            "percent_rejected": 20.0,
                            "percent_review_required": 50.0
                        }
                    ]
                }
            """
            try:
                # Build query conditions
                query_conditions = []
                
                # Add tenant filter if provided
                if tenant_id:
                    query_conditions.append(f"tenant_id = '{tenant_id}'")
                
                # Add date filter if provided (for specific day)
                if date:
                    try:
                        # Validate date format
                        datetime.strptime(date, '%Y-%m-%d')
                        query_conditions.append(f"DATE(created_at) = '{date}'")
                    except ValueError:
                        logger.error(f"Invalid date format: {date}. Expected YYYY-MM-DD")
                        return {"error": "Invalid date format. Use YYYY-MM-DD"}
                
                # Get cases with filters
                cases_data = await self._get_filtered_cases(query_conditions)
                
                if not cases_data:
                    return {
                        "date": date,
                        "tenant_id": tenant_id,
                        "total_cases": 0,
                        "summary": {
                            "total_accepted": 0,
                            "total_rejected": 0,
                            "total_review_required": 0,
                            "acceptance_rate": 0.0,
                            "rejection_rate": 0.0,
                            "review_rate": 0.0
                        },
                        "data": []
                    }
                
                # Process the data
                insights_data = self._process_insights_data(cases_data)
                
                return {
                    "date": date,
                    "tenant_id": tenant_id,
                    "total_cases": insights_data["total_cases"],
                    "summary": insights_data["summary"],
                    "data": insights_data["by_type"]
                }

            except Exception as e:
                logger.error(f"Error in get_insights: {e}", exc_info=True)
                return {"error": str(e)}

    async def _get_filtered_cases(self, conditions: List[str]) -> List[Dict[str, Any]]:
        """Get cases with applied filters."""
        try:
            # Base query
            base_query = """
            SELECT case_type, status, created_at, tenant_id, id
            FROM cases 
            WHERE deleted_at IS NULL
            """
            
            # Add conditions if any
            if conditions:
                base_query += " AND " + " AND ".join(conditions)
            
            # Order by created_at for consistency
            base_query += " ORDER BY created_at DESC"
            
            # Use raw query through RPC or fallback to Python filtering
            try:
                # If your Supabase setup supports RPC calls
                response = await self.sp_service.sp_client.rpc('execute_sql', {'query': base_query}).execute()
                return response.data if response.data else []
            except:
                # Fallback to Python filtering
                return await self._get_cases_with_python_filter(conditions)
                
        except Exception as e:
            logger.error(f"Error getting filtered cases: {e}")
            return []

    async def _get_cases_with_python_filter(self, conditions: List[str]) -> List[Dict[str, Any]]:
        """Fallback method using Python filtering."""
        try:
            # Get all cases first
            all_cases = await self.sp_service.get_from_cases_table(
                "case_type, status, created_at, tenant_id, id"
            )
            
            if not all_cases:
                return []
            
            filtered_cases = []
            
            for case in all_cases:
                include_case = True
                
                # Apply filters
                for condition in conditions:
                    if "tenant_id" in condition and case.get("tenant_id"):
                        tenant_value = condition.split("'")[1]  # Extract tenant_id from condition
                        if case["tenant_id"] != tenant_value:
                            include_case = False
                            break
                    
                    if "DATE(created_at)" in condition and case.get("created_at"):
                        date_value = condition.split("'")[1]  # Extract date from condition
                        case_date = case["created_at"][:10]  # Get YYYY-MM-DD part
                        if case_date != date_value:
                            include_case = False
                            break
                
                if include_case:
                    filtered_cases.append(case)
            
            return filtered_cases
            
        except Exception as e:
            logger.error(f"Error in Python filtering: {e}")
            return []

    def _process_insights_data(self, cases_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process raw cases data into insights format."""
        try:
            total_cases = len(cases_data)
            
            # Count by status
            status_counts = Counter([case.get("status", "unknown").upper() for case in cases_data])
            
            total_accepted = status_counts.get("ACCEPTED", 0) + status_counts.get("APPROVED", 0)
            total_rejected = status_counts.get("REJECTED", 0)
            total_review_required = status_counts.get("REVIEW_REQUIRED", 0) + status_counts.get("PENDING", 0)
            
            # Calculate percentages
            acceptance_rate = (total_accepted / total_cases * 100) if total_cases > 0 else 0.0
            rejection_rate = (total_rejected / total_cases * 100) if total_cases > 0 else 0.0
            review_rate = (total_review_required / total_cases * 100) if total_cases > 0 else 0.0
            
            # Group by case type
            type_groups = {}
            for case in cases_data:
                case_type = case.get("case_type", "unknown")
                status = case.get("status", "unknown").upper()
                
                if case_type not in type_groups:
                    type_groups[case_type] = {
                        "total": 0,
                        "accepted": 0,
                        "rejected": 0,
                        "review_required": 0
                    }
                
                type_groups[case_type]["total"] += 1
                
                if status in ["ACCEPTED", "APPROVED"]:
                    type_groups[case_type]["accepted"] += 1
                elif status == "REJECTED":
                    type_groups[case_type]["rejected"] += 1
                elif status in ["REVIEW_REQUIRED", "PENDING"]:
                    type_groups[case_type]["review_required"] += 1
            
            # Format by type data
            by_type_data = []
            for case_type, counts in type_groups.items():
                total_for_type = counts["total"]
                
                by_type_data.append({
                    "type": case_type,
                    "total_cases": total_for_type,
                    "accepted": counts["accepted"],
                    "rejected": counts["rejected"],
                    "review_required": counts["review_required"],
                    "percent_accepted": round(counts["accepted"] / total_for_type * 100, 2) if total_for_type > 0 else 0.0,
                    "percent_rejected": round(counts["rejected"] / total_for_type * 100, 2) if total_for_type > 0 else 0.0,
                    "percent_review_required": round(counts["review_required"] / total_for_type * 100, 2) if total_for_type > 0 else 0.0
                })
            
            # Sort by total cases descending
            by_type_data.sort(key=lambda x: x["total_cases"], reverse=True)
            
            return {
                "total_cases": total_cases,
                "summary": {
                    "total_accepted": total_accepted,
                    "total_rejected": total_rejected,
                    "total_review_required": total_review_required,
                    "acceptance_rate": round(acceptance_rate, 2),
                    "rejection_rate": round(rejection_rate, 2),
                    "review_rate": round(review_rate, 2)
                },
                "by_type": by_type_data
            }
            
        except Exception as e:
            logger.error(f"Error processing insights data: {e}")
            return {
                "total_cases": 0,
                "summary": {"total_accepted": 0, "total_rejected": 0, "total_review_required": 0, 
                        "acceptance_rate": 0.0, "rejection_rate": 0.0, "review_rate": 0.0},
                "by_type": []
            }
