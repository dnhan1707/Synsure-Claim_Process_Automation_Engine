from app.service.s3_service_v2 import S3Service
from app.utils.validator import Validator
from app.config.settings import get_prompt, get_settings
# from fastapi import UploadFile
# from google import genai
from openai import OpenAI
# from typing import List

class ModelService():
    def __init__(self):
        # gemini_setting = get_settings().gemini
        # self.client = genai.Client(api_key=gemini_setting.api_key)
        # self.model = gemini_setting.default_model
        # self.validator = Validator()
        
        gpt5_setting = get_settings().gpt5
        self.client = OpenAI(api_key=gpt5_setting.api_key)
        self.model = gpt5_setting.default_model
        self.validator = Validator()

    async def generate_response_v2(self, file_contents: list, manual_input: str = None):
        try:
            s3_service = S3Service()
            details = await s3_service.extract_text(file_contents)
            if manual_input:
                details += manual_input
                
            base_prompt = get_prompt(details)
            prompt = base_prompt
            # print(f"PROMPT: {prompt}")
            MAX_RETRIES = 2

            # for attempt in range(MAX_RETRIES + 1):
            #     response = self.client.models.generate_content(
            #         model=self.model,
            #         contents=prompt
            #     )
            #     is_valid, result = self.validator.validate_gemini_response(response.text)
            #     if is_valid:
            #         # await file_service.save_response(case_id, result)
            #         return result
                
            #     prompt = (
            #         base_prompt +
            #         "IMPORTANT: Your previous response was not valid JSON or did not match the required structure. "
            #         "Please respond ONLY with the correct JSON object as specified above, no extra text."
            #     )
            
            for attempt in range(MAX_RETRIES + 1):
                # Main GPT5 api call
                response = self.client.responses.create(
                    model=self.model,
                    input=[
                        {"role": "system", "content": "You are Synsure's GPT-5 claim analyst."},
                        {"role": "user", "content": prompt},
                    ],
                    reasoning={"effort": "medium"},
                    text={"verbosity": "low"},
                )
                resp = response.output_text.strip()
                is_valid, result = self.validator.validate_gemini_response(resp)
                
                if is_valid:
                    return result
                
                prompt = (
                    base_prompt +
                    "IMPORTANT: Your previous response was not valid JSON or did not match the required structure. "
                    "Please respond ONLY with the correct JSON object as specified above, no extra text."
                )

            # If all retries failed
            # return {"error": f"Invalid Gemini response after {MAX_RETRIES + 1} attempts: {result}"}
            
            return {"error": f"Invalid GPT5 response after {MAX_RETRIES + 1} attempts: {result}"}

        except Exception as e:
            return str(e)

