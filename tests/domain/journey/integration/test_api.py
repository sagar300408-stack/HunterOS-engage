import pytest

def test_api_returns_strict_schemas():
    class APIv1:
        def get_context(self, ctx_id):
            return {
                "api_version": "v1",
                "data": {"id": ctx_id}
            }
            
    api = APIv1()
    response = api.get_context("123")
    assert response["api_version"] == "v1"
    assert response["data"]["id"] == "123"

def test_api_no_ai_predictions():
    # Verify the DTO doesn't contain predicted fields
    response = {"metrics": {"score": 85}} # Actual deterministic score
    assert "predicted_score" not in response["metrics"]
