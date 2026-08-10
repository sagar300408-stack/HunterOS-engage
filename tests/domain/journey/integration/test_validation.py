import pytest

def test_validator_workspace_isolation():
    def validate_workspace(data, current_workspace):
        errors = []
        for item in data:
            if item.get("workspace_id") != current_workspace:
                errors.append(f"Isolation violation: {item.get('workspace_id')}")
        return errors
        
    data = [
        {"id": 1, "workspace_id": "ws-1"},
        {"id": 2, "workspace_id": "ws-2"}
    ]
    
    errors = validate_workspace(data, "ws-1")
    assert len(errors) == 1
    assert "Isolation violation: ws-2" in errors[0]

def test_validator_mismatched_entities():
    def validate_entities(entities):
        errors = []
        for e in entities:
            if "id" not in e:
                errors.append("Missing ID")
        return errors
        
    errors = validate_entities([{"name": "test"}])
    assert len(errors) == 1

def test_validator_does_not_raise_exceptions():
    class Validator:
        def validate(self, data):
            return {"valid": False, "validation_errors": ["Schema mismatch"]}
            
    v = Validator()
    res = v.validate({})
    assert res["valid"] is False
    assert "validation_errors" in res
