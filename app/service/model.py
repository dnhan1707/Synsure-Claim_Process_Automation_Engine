from fastapi import UploadFile
from google import genai
from dotenv import load_dotenv
from typing import List
from PyPDF2 import PdfReader
import os
import io

load_dotenv()

class ModelService():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv('GEMINI_API'))

    async def generate_response(self, files: List[UploadFile], case_type: str, case_id: str):
        try:
            file_texts = []
            for file in files:
                content = await file.read()
                # Extract text from PDF
                reader = PdfReader(io.BytesIO(content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                file_texts.append(text)

            # Combine instruction and extracted texts
            details = "".join(file_texts)
            prompt =   f"""
                You are an AI insurance claims analyst with expertise in fraud detection, policy compliance, and risk assessment. Analyze the following insurance claim and provide a comprehensive decision.

                **CLAIM INFORMATION:**
                Case Type: {case_type}
                Case ID: {case_id}

                **CLAIM DETAILS:**
                {details}

                **ANALYSIS REQUIREMENTS:**
                Evaluate the claim based on:
                1. Claim legitimacy and supporting documentation
                2. Fraud indicators and red flags
                3. Policy compliance and coverage validation
                4. Claim amount reasonableness
                5. Supporting evidence quality and consistency

                **OUTPUT FORMAT - RESPOND WITH EXACTLY THIS JSON STRUCTURE:**
                {{
                "decision": "[APPROVED|REJECTED|REVIEW_REQUIRED]",
                "reasoning": "[2-3 sentence explanation of your decision, including key factors that influenced the determination]",
                "confidence": [number between 0-100 representing confidence in decision],
                "riskScore": "[LOW|MEDIUM|HIGH]",
                "flags": ["FLAG1", "FLAG2", "FLAG3"]
                }}

                **DECISION CRITERIA:**
                - APPROVED: Clear legitimate claim with adequate documentation and low fraud risk
                - REJECTED: Clear fraud indicators or policy violations that warrant denial
                - REVIEW_REQUIRED: Borderline case needing human expert review

                **CONFIDENCE SCORING:**
                - 90-100: Very confident (clear-cut case)
                - 75-89: Confident (strong indicators)
                - 60-74: Moderate confidence (some uncertainty)
                - Below 60: Low confidence (significant uncertainty)

                **RISK SCORE GUIDELINES:**
                - LOW: Routine claim with standard risk factors
                - MEDIUM: Some elevated risk factors requiring attention
                - HIGH: Multiple risk factors or fraud indicators present

                **COMMON FLAGS TO USE:**
                Fraud-related: "FRAUD_INDICATORS", "PATTERN_SUSPICIOUS", "DOCUMENTATION_INCONSISTENT"
                Processing: "MANUAL_REVIEW_REQUIRED", "STANDARD_PROCESSING", "EXPEDITED_REVIEW"
                Evidence: "POLICE_REPORT_AVAILABLE", "MEDICAL_VERIFIED", "WITNESS_AVAILABLE", "VIDEO_EVIDENCE"
                Risk: "HIGH_VALUE_CLAIM", "REPEAT_CLAIMANT", "POLICY_RECENT"
                Verification: "THIRD_PARTY_LIABILITY", "FIRE_DEPT_VERIFIED", "COVERAGE_ADEQUATE"

                **IMPORTANT:** 
                - Respond ONLY with the JSON object
                - Do not include any markdown formatting or code blocks
                - Ensure all strings are properly quoted
                - Use exact flag names from the list above
                - Keep reasoning concise but informative
                - Base confidence on strength of evidence and clarity of case
                """

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            print(response.text)
            return response.text

        except Exception as e:
            return str(e)

    async def testgemini(self):
        # Generate content using the new API
        response = self.client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents="Explain how AI works in a few words",
        )
        print(response.text)
