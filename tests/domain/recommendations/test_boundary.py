from __future__ import annotations
import os

def test_no_predictive_ai():
    base_dir = "app/domain/recommendations"
    if not os.path.exists(base_dir):
        return
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    content = f.read()
                    assert "openai" not in content
                    assert "langchain" not in content
