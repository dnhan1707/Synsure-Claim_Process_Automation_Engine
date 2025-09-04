from fastapi import UploadFile
from typing import List, Optional, Dict, Any
from app.service.supabase_service import SupabaseService
from app.service.s3_service import FileService
from app.service.case_service import CaseService

# This controller include the logic of the route
class CaseControllerV2():
    def __init__(self):
        self.sp_service = SupabaseService()
        self.case_service = CaseService()
        self.file_service =  FileService()

    async def get_cases(self) -> List[Dict[str, Any]]:
        # return List[{id:..., case_name:...}]
        try:
            case_list = await self.sp_service.get_all_name_id(table_name="case")
            return case_list
        except Exception as e:
            return []

    async def get_latest_response(self, case_id: str) -> Dict[str, Any]:
        try:
            latest_response = await self.sp_service.get_latest_response_by_case_id(case_id)
            if not latest_response or not latest_response.get("s3_link"):
                return {"success": False, "error": "No response found"}

            s3_key = latest_response["s3_link"]
            content = await self.file_service.extract_content(s3_key)
            return content

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_case(
            self, 
            case_id: Optional[str], 
            case_name: str, 
            manual_inputs: Optional[str], 
            files: Optional[List[UploadFile]]
        ) -> Dict[str, Any]:
        try:
            # If no case_id, create a new case
            if not case_id:
                case_row = await self.sp_service.insert(table_name="case", object={"case_name": case_name})
                case_id = case_row["id"] if case_row and "id" in case_row else None
                if not case_id:
                    return {"success": False, "error": "Failed to create case."}

            await self.case_service.save_manual_and_files(case_id=case_id, case_name=case_name, manual_inputs=manual_inputs, files=files, response_data_id=None)

            return {"success": True, "case_id": case_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_case(self, case_id: str, new_case_name: str) -> Dict[str, Any]:
        try:
            case_row = await self.sp_service.update(table_name="case", id=case_id, objects={"case_name": new_case_name})
            case_id = case_row["id"] if case_row and "id" in case_row else None
            if not case_id:
                return {"success": False, "error": "Failed to update case."}
            return {"success": True, "case_id": case_id, "case_name": new_case_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete(self, case_ids: List[str]) -> Dict[str, Any]:
        # update the is_active column to be False for all provided case_ids
        try:
            results = []
            for case_id in case_ids:
                case_row = await self.sp_service.update(table_name="case", id=case_id, objects={"is_active": False})
                case_id_returned = case_row["id"] if case_row and "id" in case_row else None
                if not case_id_returned:
                    results.append({"case_id": case_id, "success": False, "error": "Failed to update case."})
                else:
                    results.append({"case_id": case_id_returned, "success": True, "is_active": False})
            return {"results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}
        

    async def submit_one_case(
        self,
        case_id: Optional[str],
        case_name: Optional[str],
        manual_input: Optional[str],
        files: Optional[List[UploadFile]]
    ) -> Dict[str, Any]:
        try:
            '''
            if no case_id -> this is new case:
                respose = proceed with model
                    - extract text from pdf
                    - combine with manual text
                    - create prompt
                    - generate response with validator:
                        if valid -> return
                        if not retry

                save into s3:
                    - update response table with its s3_link
                    - extract id
                    - save new files into s3
                    - update files table with response_id
                        
            else this is existed case:
                if having new input or new files, 
                    proceed with model
                else:
                    proceed with history files
            '''
            if not case_id or case_id == "":
                # create a case
                case_row = await self.sp_service.insert(table_name="case", object={"case_name": case_name})
                case_id = case_row["id"] if case_row and "id" in case_row else None
                result = await self.case_service.proceed_with_model(case_id, case_name, manual_input, files)
                return result, case_id
            
            else:
                if manual_input or files:
                    result = await self.case_service.proceed_with_model(case_id, case_name, manual_input, files)
                    return result, case_id
            
                else:
                    result = await self.case_service.proceed_with_model_history_files(case_id)
                    return result, case_id


        except Exception as e:
            return {"success": False, "error submit one case function": str(e)}

    async def submit_bulk(self, case_ids: List[str]) -> Dict[str, Any]:
        try:
            for id in case_ids:
                await self.case_service.proceed_with_model_history_files(id)
            
            return {"success": True}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
