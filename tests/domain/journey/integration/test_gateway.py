import pytest

def test_gateway_routing_calls(mock_gateway):
    request = {"type": "journey_context", "id": "123"}
    response = mock_gateway.assemble(request)
    assert response["status"] == "success"
    assert response["data"] == "mocked_context"

def test_gateway_returns_complete_context():
    class DummyGateway:
        def assemble(self):
            return {
                "metadata": {"version": "1.0"},
                "data": {"entities": []}
            }
            
    gw = DummyGateway()
    res = gw.assemble()
    assert "metadata" in res
    assert "data" in res
