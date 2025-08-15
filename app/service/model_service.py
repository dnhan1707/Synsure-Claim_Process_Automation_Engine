from app.service.s3_service import FileService
from app.utils.validator import Validator
from app.config.settings import get_prompt, get_settings
# from fastapi import UploadFile
from google import genai
# from typing import List

class ModelService():
    def __init__(self):
        gemini_setting = get_settings().gemini
        self.client = genai.Client(api_key=gemini_setting.api_key)
        self.model = gemini_setting.default_model
        self.validator = Validator()


    async def generate_response_v2(self, file_contents: list, manual_input: str):
        try:
            file_service = FileService()
            details = await file_service.extract_text(file_contents)
            details += manual_input
            base_prompt = get_prompt(details)
            prompt = base_prompt
            MAX_RETRIES = 2

            for attempt in range(MAX_RETRIES + 1):
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                is_valid, result = self.validator.validate_gemini_response(response.text)
                if is_valid:
                    # await file_service.save_response(case_id, result)
                    return result
                
                prompt = (
                    base_prompt +
                    "IMPORTANT: Your previous response was not valid JSON or did not match the required structure. "
                    "Please respond ONLY with the correct JSON object as specified above, no extra text."
                )

            # If all retries failed
            return {"error": f"Invalid Gemini response after {MAX_RETRIES + 1} attempts: {result}"}

        except Exception as e:
            return str(e)

