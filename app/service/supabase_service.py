from app.config.settings import get_settings
from supabase import Client, create_client
from typing import Dict, Any, List
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
            logger.error(f"Error get_case {e}")
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
            logger.error(f"Error get_case {e}")
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