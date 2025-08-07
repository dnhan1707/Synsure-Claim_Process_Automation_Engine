import json

class Validator():
    def __init__(self):
        self.gemini_response_expected_keys = {"decision", "reasoning", "confidence", "riskScore", "flags"}

    def validate_gemini_response(self, response_text: str):
        try:
            data = json.loads(response_text)
            if not isinstance(data, dict):
                return False, "Not a JSON object"
            missing = self.gemini_response_expected_keys - data.keys()
            if missing:
                return False, f"Missing keys: {missing}"
            
            return True, data
        except Exception as e:
            return False, str(e)

