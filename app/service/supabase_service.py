from app.config.settings import get_settings
from supabase import Client, create_client
from typing import Dict, Any, List


class SupabaseService():
    def __init__(self):
        setting = get_settings()
        sp_setting = setting.supabase
        url, key = "", ""

        if setting.env and setting.env == "development":
            url, key = sp_setting.url_development, sp_setting.api_key_development
            print("using developemt supabase development")
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
            return {"error": str(e)}

    
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
                .eq("is_active", True)
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
                .select("s3_link")
                .eq("case_id", case_id)
                .eq("is_active", True)
                .execute()
            )
            # Deduplicate by s3_link
            seen = set()
            unique_files = []
            for row in response.data if response.data else []:
                s3_link = row.get("s3_link")
                if s3_link and s3_link not in seen:
                    seen.add(s3_link)
                    unique_files.append(row)
            return unique_files
        except Exception as e:
            return []

    async def get_responses_by_case_id(self, case_id: str):
        try:
            response = (
                self.sp_client.table("response")
                .select("s3_link")
                .eq("case_id", case_id)
                .eq("is_active", True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            return []
        
    async def get_latest_response_by_case_id(self, case_id: str):
        try:
            response = (
                self.sp_client.table("response")
                .select("id, s3_link, created_at")
                .eq("case_id", case_id)
                .eq("is_active", True)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            return None
        
        except Exception as e:
            return {"error": str(e)}
