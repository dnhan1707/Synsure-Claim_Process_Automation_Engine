from pydantic import BaseModel, Field
from dotenv import load_dotenv
from functools import lru_cache
import os

load_dotenv()

class GeminiSettings(BaseModel):
    api_key: str = Field(default_factory=lambda: os.getenv('GEMINI_API'))
    default_model: str = Field(default='gemini-2.5-flash')
    

class EmailSettings(BaseModel):
    demo_email_user: str = Field(default_factory=lambda: os.getenv("DEMO_EMAIL_USER"))
    demo_email_pass: str = Field(default_factory=lambda: os.getenv("DEMO_EMAIL_PASS"))


class S3Settings(BaseModel):
    service_name: str = Field(default="s3")
    aws_access_key_id: str = Field(default_factory=lambda: os.getenv("AWS_ACCESS_KEY"))
    aws_secret_access_key: str = Field(default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY"))
    region_name: str = Field(default_factory=lambda: os.getenv("AWS_REGION"))
    bucket_name: str = Field(default_factory=lambda: os.getenv("AWS_BUCKET_NAME"))
    bucket_name_development: str = Field(default_factory=lambda: os.getenv("AWS_BUCKET_NAME_DEVELOPMENT"))


class SupabaseSetting(BaseModel):
    url: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL"))
    api_key: str = Field(default_factory=lambda: os.getenv("SUPABASE_API_KEY"))
    url_development: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL_DEVELOPMENT"))
    api_key_development: str = Field(default_factory=lambda: os.getenv("SUPABASE_API_KEY_DEVELOPMENT"))


class RedisSetting(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv("REDIS_HOST"))
    password: str = Field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    port: str = Field(default_factory=lambda: os.getenv("REDIS_PORT"))


class Settings(BaseModel):
    env: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT"))
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    supabase: SupabaseSetting = Field(default_factory=SupabaseSetting)
    s3: S3Settings = Field(default_factory=S3Settings)
    redis: RedisSetting = Field(default_factory=RedisSetting)


@lru_cache
def get_settings() -> Settings:
    try:
        settings = Settings()
        return settings
    except Exception as e:
        return {"error": e}
        

def get_prompt(details: str):
    prompt = f"""
        You are an AI insurance claims analyst with expertise in fraud detection, policy compliance, and risk assessment. Analyze the following insurance claim and provide a comprehensive decision.

        **IMPORTANT:**
        - If CLAIM DETAILS is empty or missing, respond ONLY with the JSON object below, using:
            - "decision": "REVIEW_REQUIRED"
            - "reasoning": "No claim details or supporting documentation were provided for analysis. This case requires immediate human expert intervention to gather necessary data."
            - "confidence": 50
            - "riskScore": "HIGH"
            - "flags": ["MANUAL_REVIEW_REQUIRED"]
        - Do not include any markdown formatting or code blocks.
        - Ensure all strings are properly quoted.
        - Use exact flag names from the list below.
        - Keep reasoning concise but informative.
        - Base confidence on strength of evidence and clarity of case.

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
    """
    return prompt


