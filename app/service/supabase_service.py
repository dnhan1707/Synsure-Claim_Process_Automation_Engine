from app.config.settings import get_settings
from supabase import Client, create_client
from typing import Dict, Any, List, Optional
import logging
import re
import os

logger = logging.getLogger(__name__)

class SupabaseService():
    def __init__(self):
        setting = get_settings()
        sp_setting = setting.supabase
        url, key = "", ""

        if setting.env and setting.env == "development":
            url, key = sp_setting.url_development, sp_setting.api_key_development
            # print("using developemt supabase development")
        else:
            url, key = sp_setting.url, sp_setting.api_key

        self.sp_client: Client = create_client(url, key)

    
    async def insert(self, table_name: str, object: Dict[str, Any]):
        try:
            response = (
                self.sp_client.table(table_name)
                .insert(object)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            return None
        
        except Exception as e:
            return {"error inserting": str(e)}


    async def insert_bulk(self, table_name: str, objects: List[Dict]):
        try:
            response = (
                self.sp_client.table(table_name)
                .insert(objects)
                .execute()
            )
            return response.data 
        except Exception as e:
            return None

    
    async def update(self, table_name: str, id: str, objects: Dict[str, Any]):
        try:
            response = (
                self.sp_client.table(table_name)
                .update(objects)
                .eq("id", id)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None 
        except Exception as e:
            return {"error": str(e)}

    
    async def get_all_name_id(self, table_name: str):
        try:
            response = (
                self.sp_client.table(table_name)
                .select("id, case_name")
                .is_("deleted_at", "null")
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data
            return [] 
        except Exception as e:
            return {"error": str(e)}
    

    async def get_files_by_case_id(self, case_id: str):
        try:            
            response = (
                self.sp_client.table("files")
                .select("id, case_id, tenant_id, name, s3_key, s3_bucket, kind, uploaded_at")  # Fixed: s3_key not s3_link
                .eq("case_id", case_id)
                .is_("deleted_at", "null")  # Fixed: use is_() for null checks
                .execute()
            )
            
            
            if response.data and len(response.data) > 0:
                
                # Deduplicate by s3_key if needed
                seen = set()
                unique_files = []
                for row in response.data:
                    s3_key = row.get("s3_key")  # Fixed: s3_key not s3_link
                    if s3_key and s3_key not in seen:
                        seen.add(s3_key)
                        unique_files.append(row)

                return unique_files
            else:
                return []
                
        except Exception as e:
            return []


    async def get_responses_by_case_id(self, case_id: str):
        try:
            response = (
                self.sp_client.table("responses")
                .select("id, s3_link, case_id")
                .eq("case_id", case_id)
                .is_("deleted_at", "null")
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            return []
        

    async def get_latest_response_by_case_id(self, case_id: str):
        try:
            response = (
                self.sp_client.table("responses")
                .select("id, s3_link, created_at")
                .eq("case_id", case_id)
                .is_("deleted_at", "null")
                .order("uploaded_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            return None
        
        except Exception as e:
            return {"error": str(e)}


    async def get_all_files(self, table_name: str, case_id: str, tenant_id: str, columns: str):
        try:
            response = (
                self.sp_client.table(table_name)
                .select(columns)
                .eq("case_id", case_id)
                .eq("tenant_id", tenant_id)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data

            return None

        except Exception as e:
            return None


    async def get_all(self, table_name: str, columns: str):
        try:
            response = (
                self.sp_client.table(table_name)
                .select(columns)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data

            return None

        except Exception as e:
            print("Supabase Service Error - get_all", e)
            return None
        

    async def get_all_claim_by_tenant_id(self, table_name: str, tenant_id: str, columns: str):
        try:
            response = (
                self.sp_client.table(table_name)
                .select(columns)
                .eq("tenant_id", tenant_id)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data

            return None

        except Exception as e:
            print("Supabase Service Error - get_all", e)
            return None
    
    
    async def get_row_by_id(self, id: str, table_name: str, columns: str):
        try:
            response = (
                self.sp_client.table(table_name)
                .select(columns)
                .eq("id", id)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            print("Supabase Service Error - get_all", e)
            return None
    

    async def count_file(self, tenant_id: str, case_id: str, filename: str):
        try:
            response = (
                self.sp_client.table("files")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("case_id", case_id)
                .eq("name", filename)
                .is_("deleted_at", "null")
                .execute()
            )

            if response.data and len(response.data) > 0:
                return len(response.data)

            return 0

        except Exception as e:
            return -1
        

    async def get_files_by_name(self, tenant_id: str, case_id: str, filename: str):
        try:
            response = (
                self.sp_client.table("files")
                .select("id, name, s3_key, s3_bucket, tenant_id, case_id, uploaded_at")
                .eq("tenant_id", tenant_id)
                .eq("case_id", case_id)
                .eq("name", filename)
                .is_("deleted_at", "null")
                .order("uploaded_at", desc=True)  # Get latest first
                .execute()
            )
            
            if response.data:
                return response.data
            return []
            
        except Exception as e:
            return []



class SupabaseServiceV2():
    def __init__(self):
        setting = get_settings()
        sp_setting = setting.supabase
        url, key = "", ""

        if setting.env and setting.env == "development":
            url, key = sp_setting.url_development, sp_setting.api_key_development
            # print("using developemt supabase development")
        else:
            url, key = sp_setting.url, sp_setting.api_key

        self.sp_client: Client = create_client(url, key)

    async def get_all_cases_by_tenant(self, table_name: str, columns: str, tenant_id: str, available: bool = True):
        try:
            if available:
                response = (
                    self.sp_client.table(table_name)
                    .select(columns)
                    .eq("tenant_id", tenant_id)
                    .is_("deleted_at", "null")
                    .execute()
                )
                
                if response.data and len(response.data) > 0:
                    return response.data
            
            else:
                response = (
                    self.sp_client.table(table_name)
                    .select(columns)
                    .eq("tenant_id", tenant_id)
                    .execute()
                )
                
                if response.data and len(response.data) > 0:
                    return response.data

            return None

        except Exception as e:
            logger.error(f"Error get_all_cases_by_tenant {e}")
            return None

    async def get_case(self, table_name: str, columns: str, tenant_id: str, case_id: str):
        try:
            response = (
                    self.sp_client.table(table_name)
                    .select(columns)
                    .eq("tenant_id", tenant_id)
                    .eq("id", case_id)
                    .is_("deleted_at", "null")
                    .execute()
                )
                    
            if response.data and len(response.data) > 0:
                return response.data[0]        
        
        except Exception as e:
            logger.error(f"Error get_case {e}")
            return None
        
    async def get_s3_keys(self, table_name: str, columns: str, tenant_id: str, case_id: str):
        try:
            response = (
                    self.sp_client.table(table_name)
                    .select(columns)
                    .eq("tenant_id", tenant_id)
                    .eq("case_id", case_id)
                    .is_("deleted_at", "null")
                    .execute()
                )
                    
            if response.data and len(response.data) > 0:
                return response.data    
        
        except Exception as e:
            logger.error(f"Error get_s3_keys {e}")
            return None
    
    async def get_by_id(self, table_name: str, columns: str, id: str):
        try:
            response = (
                    self.sp_client.table(table_name)
                    .select(columns)
                    .eq("id", id)
                    .is_("deleted_at", "null")
                    .execute()
                )
                    
            if response.data and len(response.data) > 0:
                return response.data[0]    

            return None
        
        except Exception as e:
            logger.error(f"Error get_by_id {e}")
            return None

    
    async def insert_one(self, table_name: str, object: dict) -> str:
        try:
            response = (
                self.sp_client.table(table_name)
                .insert(object)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            logger.error(f"Error insert_one: {e}")
            return None
        
    async def insert_bulk(self, table_name: str, list_object: list[dict]) -> str:
        try:
            response = (
                self.sp_client.table(table_name)
                .insert(list_object)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data

            return None

        except Exception as e:
            logger.error(f"Error insert_one: {e}")
            return None
        
    
    async def find_duplicates_by_filename(self, table_name: str, columns: str, tenant_id: str, case_id: str, target_filename: str):
        base_filename = self.normalize_filename(target_filename)

        try:
            response = (
                self.sp_client.table(table_name)
                .select(columns)
                .eq("tenant_id", tenant_id)
                .eq("case_id", case_id)
                .ilike("name", f"{base_filename.replace('.','%')}")
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data

            return []

        except Exception as e:
            logger.error(f"Error find_duplicates_by_filename: {e}")
            return []

    def normalize_filename(self, filename: str) -> str:
        name, ext = os.path.splitext(filename)
        # remove ' (n)' at the end of filename if exists
        normalized = re.sub(r"\s\(\d+\)$", "", name)
        return f"{normalized}{ext}"

    async def get_latest_response(self, tenant_id: str, case_id: str):
        try:
            response = (
                self.sp_client.table("responses")
                .select("id, s3_key, started_at")
                .eq("tenant_id", tenant_id)
                .eq("case_id", case_id)
                .is_("deleted_at", "null")
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            return None
        
        except Exception as e:
            return None
        
    async def get_file_by_case_tenant_id(self, tenant_id: str, case_id: str, columns: str):
        try:
            response = (
                self.sp_client.table("files")
                .select(columns)
                .eq("tenant_id", tenant_id)
                .eq("case_id", case_id)
                .is_("deleted_at", "null")
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data
            
            return None
        except Exception as e:
            return None
        

    async def update(self, table_name: str, id: str, object: dict):
        """Update a record by ID."""
        try:
            response = (
                self.sp_client.table(table_name)
                .update(object)
                .eq("id", id)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating {table_name}: {e}")
            return None

    async def update_task_status(self, task_id: str, status: str, **kwargs):
        """Update task status with optional additional fields."""
        try:
            update_data = {"status": status}
            
            # Add optional fields
            if "started_at" in kwargs:
                update_data["started_at"] = kwargs["started_at"]
            if "completed_at" in kwargs:
                update_data["completed_at"] = kwargs["completed_at"]
            if "error_message" in kwargs:
                update_data["error_message"] = kwargs["error_message"]
            if "response_id" in kwargs:
                update_data["response_id"] = kwargs["response_id"]
            
            response = (
                self.sp_client.table("task")
                .update(update_data)
                .eq("id", task_id)
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                logger.info(f"Task {task_id} status updated to {status}")
                return response.data[0]
            else:
                logger.warning(f"No task updated for ID {task_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {e}")
            return None
        

    async def batch_update_cases(self, case_updates: list[dict]):
        """Batch update multiple cases efficiently."""
        try:
            # Use Supabase batch update or loop with minimal overhead
            for update in case_updates:
                await self.update("cases", update["id"], {"status": update["status"]})
            return True
        except Exception as e:
            logger.error(f"Error in batch_update_cases: {e}")
            return False


    async def update_task_and_case_status(self, task_id: str, case_id: str, 
                                        task_status: str, case_status: str, **kwargs):
        """Atomically update both task and case status."""
        try:
            # Update task
            await self.update_task_status(task_id=task_id, status=task_status, **kwargs)
            
            # Update case
            await self.update(table_name="cases", id=case_id, object={"status": case_status})
            
            return True
        except Exception as e:
            logger.error(f"Error updating task and case status: {e}")
            return False
    

    async def update_new_case_processed_column(self, tenant_id: str, case_id: str, bool_val: bool):
        try:
            response = (
                self.sp_client.table("cases")
                .update({"new_case_processed": bool_val})
                .eq("tenant_id", tenant_id)
                .eq("id", case_id)
                .is_("deleted_at", "null")
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            else:
                return False

        except Exception as e:
            logger.error(f"Error uupdate_new_case_processed_column: {e}")
            return False

    
    async def delete_by_tenant_id_case_id(self, table_name: str, tenant_id: str, case_id: str, soft_delete: bool = True):
        """
        Delete records by tenant_id and case_id, returning the IDs of deleted records.
        """
        try:
            if soft_delete:
                # Soft delete: Update deleted_at column with current timestamp
                if table_name == "cases":
                    response = (
                        self.sp_client.table(table_name)
                        .update({"deleted_at": "now()"})
                        .eq("tenant_id", tenant_id)
                        .eq("id", case_id)
                        .is_("deleted_at", "null")  
                        .execute()
                    )
                else:
                    response = (
                        self.sp_client.table(table_name)
                        .update({"deleted_at": "now()"})
                        .eq("tenant_id", tenant_id)
                        .eq("case_id", case_id)
                        .is_("deleted_at", "null")  
                        .execute()
                    )
                
                if response.data:
                    deleted_ids = [record["id"] for record in response.data]
                    logger.info(f"Soft deleted {len(deleted_ids)} records from {table_name} for tenant {tenant_id}, case {case_id}. IDs: {deleted_ids}")
                    return deleted_ids
                else:
                    logger.info(f"No records found to soft delete from {table_name} for tenant {tenant_id}, case {case_id}")
                    return []
            else:
                # Hard delete: Permanently remove records

                if table_name == "cases":
                    response = (
                        self.sp_client.table(table_name)
                        .delete()
                        .eq("tenant_id", tenant_id)
                        .eq("id", case_id)
                        .is_("deleted_at", "null")  
                        .execute()
                    )
                else:
                    response = (
                        self.sp_client.table(table_name)
                        .delete()
                        .eq("tenant_id", tenant_id)
                        .eq("case_id", case_id)
                        .execute()
                    )
                
                if response.data:
                    deleted_ids = [record["id"] for record in response.data]
                    logger.info(f"Hard deleted {len(deleted_ids)} records from {table_name} for tenant {tenant_id}, case {case_id}. IDs: {deleted_ids}")
                    return deleted_ids
                else:
                    logger.info(f"No records found to hard delete from {table_name} for tenant {tenant_id}, case {case_id}")
                    return []

        except Exception as e:
            logger.error(f"Error delete_by_tenant_id_case_id: {e}")
            return []
        
        
    async def delete_by_response_id(self, table_name: str, response_id: str, soft_delete: bool = True):
        """
        Delete records by response_id, returning the IDs of deleted records.
        """
        try:
            if soft_delete:
                response = (
                    self.sp_client.table(table_name)
                    .update({"deleted_at": "now()"})
                    .eq("response_id", response_id)
                    .is_("deleted_at", "null")
                    .execute()
                )
            else:
                response = (
                    self.sp_client.table(table_name)
                    .delete()
                    .eq("response_id", response_id)
                    .execute()
                )
                
            if response.data:
                deleted_ids = [record["id"] for record in response.data]
                logger.info(f"{'Soft' if soft_delete else 'Hard'} deleted {len(deleted_ids)} records from {table_name} for response {response_id}")
                return deleted_ids
            else:
                logger.info(f"No records found to delete from {table_name} for response {response_id}")
                return []

        except Exception as e:
            logger.error(f"Error delete_by_response_id: {e}")
            return []
        

    async def get_by_tenant_id(self, table_name: str, tenant_id: str, column: str):
        try:
            response = (
                self.sp_client.table(table_name)
                .select(column)
                .eq("tenant_id", tenant_id)
                .is_("deleted_at", "null")
                .execute()
            )

            if response.data:
                return response.data
            
            return []

        except Exception as e:
            logger.error(f"Error get_by_tenant_id: {e}")
            return []
        

    async def get_from_cases_table(self, column: str):
        try:
            response = (
                self.sp_client.table("cases")
                .select(column)
                .is_("deleted_at", "null")
                .execute()
            )

            if response.data:
                return response.data
            
            return []

        except Exception as e:
            logger.error(f"Error get_by_tenant_id: {e}")
            return []
    
    # async def get_distict_type_from_cases_table(self, column: str):
    #     try:
    #         response = (
    #             self.sp_client.table("cases")
    #             .select(column, distinct=True)
    #             .is_("deleted_at", "null")
    #             .execute()
    #         )

    #         if response.data:
    #             return response.data
            
    #         return []

    #     except Exception as e:
    #         logger.error(f"Error get_distict_type_from_cases_table: {e}")
    #         return []

    async def get_case_with_status(self, column: str, status: str):
        try:
            response = (
                self.sp_client.table("cases")
                .select(column)
                .eq("status", status)
                .is_("deleted_at", "null")
                .execute()
            )

            if len(response.data) > 0 and response.data[0]:
                return response.data
            
            return []
        
        except Exception as e:
            logger.error(f"Error get_case_with_status")
            return [] 

    

    async def is_new_case_processed(self, tenant_id: str, case_id: str):
        try:
            response = (
                self.sp_client.table("cases")
                .select("new_case_processed")
                .eq("tenant_id", tenant_id)
                .eq("id", case_id)
                .is_("deleted_at", "null")
                .execute()
            )

            if len(response.data) > 0 and response.data[0]:
                return response.data[0].get("new_case_processed")
            
            return False
        
        except Exception as e:
            logger.error(f"Error is_new_case_processed")
            return False
        


    async def get_all_cases(self, columns: str, available: bool = True):
        try:
            q = self.sp_client.table("cases").select(columns)
            if available:
                q = q.is_("deleted_at", "null")
            response = q.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error get_all_cases: {e}")
            return []

    async def get_case_by_id(self, columns: str, case_id: str):
        try:
            response = (
                self.sp_client.table("cases")
                .select(columns)
                .eq("id", case_id)
                .is_("deleted_at", "null")
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error get_case_by_id: {e}")
            return None

    async def get_tenants_by_name(self, name_query: str, columns: str = "id, name"):
        try:
            response = (
                self.sp_client.table("tenants")
                .select(columns)
                .ilike("name", f"%{name_query}%")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error get_tenants_by_name: {e}")
            return []

    async def get_tenants_by_ids(self, tenant_ids: list[str], columns: str = "id, name"):
        if not tenant_ids:
            return []
        try:
            response = (
                self.sp_client.table("tenants")
                .select(columns)
                .in_("id", tenant_ids)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error get_tenants_by_ids: {e}")
            return []
        

    async def get_files_by_case_id(self, columns: str, case_id: str):
        try:
            response = (
                self.sp_client.table("files")
                .select(columns)
                .eq("case_id", case_id)
                .is_("deleted_at", "null")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error get_files_by_case_id: {e}")
            return []


    async def search_cases(self, q: str, columns: str, tenant_id: str | None = None):
        """
        Search across cases.case_name, cases.short_des, and tenants.name.
        Returns unique cases.
        """
        try:
            cols = columns
            if "tenant_id" not in [c.strip() for c in columns.split(",")]:
                cols = f"tenant_id, {columns}"

            results_by_id: dict[str, dict] = {}

            # 1) Text search on cases.case_name
            resp_name = (
                self.sp_client.table("cases")
                .select(cols)
                .ilike("case_name", f"%{q}%")
                .is_("deleted_at", "null")
                .execute()
            )
            for r in resp_name.data or []:
                results_by_id[r["id"]] = r

            # 2) Text search on cases.short_des
            resp_desc = (
                self.sp_client.table("cases")
                .select(cols)
                .ilike("short_des", f"%{q}%")
                .is_("deleted_at", "null")
                .execute()
            )
            for r in resp_desc.data or []:
                results_by_id[r["id"]] = r

            # 3) Tenants.name search → then fetch cases by those tenant_ids
            tenants = await self.get_tenants_by_name(q, columns="id, name")
            tenant_ids = [t["id"] for t in tenants]
            if tenant_ids:
                resp_tenants = (
                    self.sp_client.table("cases")
                    .select(cols)
                    .in_("tenant_id", tenant_ids)
                    .is_("deleted_at", "null")
                    .execute()
                )
                for r in resp_tenants.data or []:
                    results_by_id[r["id"]] = r

            final = list(results_by_id.values())
            if tenant_id:
                final = [c for c in final if c.get("tenant_id") == tenant_id]

            return final
        except Exception as e:
            logger.error(f"Error search_cases: {e}")
            return []
        