import pytest

def test_executive_strategy_filters_properly():
    source_data = [
        {"type": "financial", "value": 1000},
        {"type": "operational", "value": 500},
        {"type": "technical", "value": 100}
    ]
    
    def apply_executive_strategy(data):
        # Should not modify source, returns filtered subset
        return [d for d in data if d["type"] in ("financial", "operational")]
        
    filtered = apply_executive_strategy(source_data)
    assert len(filtered) == 2
    assert "technical" not in [d["type"] for d in filtered]
    assert len(source_data) == 3 # Source unmodified

def test_sales_strategy_filters_properly():
    source_data = [
        {"role": "buyer", "id": 1},
        {"role": "engineer", "id": 2}
    ]
    
    def apply_sales_strategy(data):
        return [d for d in data if d["role"] == "buyer"]
        
    filtered = apply_sales_strategy(source_data)
    assert len(filtered) == 1
    assert filtered[0]["id"] == 1
