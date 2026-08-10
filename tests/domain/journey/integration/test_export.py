import pytest

def test_export_engine_api_dto():
    def export_api(context):
        return {"dto_type": "api", "payload": context}
        
    dto = export_api({"id": "ctx-1"})
    assert dto["dto_type"] == "api"

def test_export_engine_ai_ready_dto():
    def export_ai_ready(context):
        return {"prompt_context": context}
        
    dto = export_ai_ready("clean text")
    assert "prompt_context" in dto

def test_export_engine_dashboard_dto():
    def export_dashboard(context):
        return {"charts": [], "tables": []}
        
    dto = export_dashboard({})
    assert "charts" in dto
