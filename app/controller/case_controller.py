from app.service.file import FileService
from app.service.model import ModelService
from fastapi import UploadFile
from typing import List, Optional
import uuid
import asyncio

file_service = FileService()
model_service = ModelService()

class CaseController():
    async def list_cases(self):
        return await file_service.get_cases_info()

    async def get_case_files_links(self, case_id: str):
        return await file_service.get_case_files_links(case_id)

    async def handle_submit_one_case(
        self,
        case_id: Optional[str],
        case_name: Optional[str],
        manual_input: Optional[str],
        files: Optional[List[UploadFile]]
    ):
        if not case_id or case_id == "":
            case_id = str(uuid.uuid4())
            if not files or len(files) == 0:
                return {"error": "Files are required for new cases.", "status_code": 400}
            file_contents = []
            for file in files:
                content = await file.read()
                file_contents.append({"filename": file.filename, "content": content})
        else:
            file_contents = []
            if files and len(files) > 0:
                for file in files:
                    content = await file.read()
                    file_contents.append({"filename": file.filename, "content": content})
                # Always check S3 for manual_input if not provided
                if not manual_input:
                    _, manual_input_s3 = await file_service.get_case_data(case_id)
                    if manual_input_s3:
                        manual_input = manual_input_s3
            else:
                file_contents, manual_input_s3 = await file_service.get_case_data(case_id)
                if not manual_input:
                    manual_input = manual_input_s3

        details = await file_service.extract_text(file_contents)
        details += manual_input or ""
        await file_service.save(case_id, case_name, file_contents, manual_input)
        result = await model_service.generate_response(file_contents, manual_input, case_id)
        return {"result": result, "status_code": 200}

    async def handle_submit_bulk_case(self, case_ids: List[str]):
        semaphore = asyncio.Semaphore(5)
        async def process_case(case_id):
            async with semaphore:
                file_contents, manual_text = await file_service.get_case_data(case_id)
                result = await model_service.generate_response(file_contents, manual_text, case_id)
                return {"case_id": case_id, "result": result}
        results = await asyncio.gather(*(process_case(cid) for cid in case_ids))
        return results

    async def save_case(
        self,
        case_id: Optional[str],
        case_name: Optional[str],
        files: Optional[List[UploadFile]],
        manual_input: Optional[str]
    ):
        has_files = files and len(files) > 0
        has_manual = manual_input is not None and manual_input != ""
        has_case_name = case_name is not None and case_name != ""

        if not has_files and not has_manual and not has_case_name:
            return {"error": "No data to save.", "status_code": 400}

        if not case_id or case_id == "":
            case_id = str(uuid.uuid4())

        file_contents = []
        if has_files:
            for file in files:
                content = await file.read()
                file_contents.append({"filename": file.filename, "content": content})
        
        await file_service.save(case_id, case_name, file_contents, manual_input)
        
        return {"success": True, "case_id": case_id}