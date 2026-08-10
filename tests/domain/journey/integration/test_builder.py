import pytest

def test_builder_assembling_blocks():
    class MockBuilder:
        def __init__(self):
            self.blocks = []
        def add_block(self, block):
            self.blocks.append(block)
            return self
        def build(self):
            return {"blocks": self.blocks}
            
    builder = MockBuilder()
    res = builder.add_block("timeline").add_block("entities").build()
    assert "timeline" in res["blocks"]
    assert "entities" in res["blocks"]

def test_builder_completeness_scoring():
    def score_context(ctx):
        if not ctx.get("blocks"):
            return 0.0
        return len(ctx["blocks"]) / 5.0
        
    assert score_context({"blocks": ["a", "b"]}) == 0.4
    assert score_context({"blocks": []}) == 0.0

def test_builder_provenance_generation():
    def generate_provenance(steps):
        return [f"step:{s}" for s in steps]
        
    prov = generate_provenance(["init", "fetch", "score"])
    assert prov == ["step:init", "step:fetch", "step:score"]
