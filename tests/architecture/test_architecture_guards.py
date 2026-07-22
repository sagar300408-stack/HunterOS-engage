import ast
import os
import pytest
from pathlib import Path

def test_no_direct_service_calls_across_domains():
    """
    Ensures that domain services do not directly instantiate or call other domain engines.
    Communication MUST go through the EventBus.
    """
    project_root = Path(__file__).parent.parent.parent / "app" / "domain"
    
    forbidden_imports = [
        "InsightEngine",
        "KpiIntelligenceEngine",
        "OperationalHealthEngine",
        "FollowUpEngine",
    ]
    
    violations = []
    
    for py_file in project_root.rglob("*.py"):
        # Ignore tests and bootstrap files
        if "test" in py_file.name or py_file.name == "bootstrap.py":
            continue
            
        content = py_file.read_text(encoding="utf-8")
        
        # Parse AST to check imports
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
            
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in forbidden_imports:
                        # Allow self-imports (e.g., insight domain importing InsightEngine)
                        if "app.domain.insight" in str(node.module) and alias.name == "InsightEngine":
                            continue
                        if "app.domain.intelligence.engines.insight" in str(node.module) and alias.name == "InsightEngine":
                            continue
                        if "app.domain.kpi" in str(node.module) and alias.name == "KpiIntelligenceEngine":
                            continue
                        if "app.domain.health" in str(node.module) and alias.name == "OperationalHealthEngine":
                            continue
                        if "app.domain.followup" in str(node.module) and alias.name == "FollowUpEngine":
                            continue
                        
                        violations.append(f"{py_file.name}: directly imported {alias.name}")
                        
    assert not violations, f"Architecture Violation found: {violations}"

def test_all_consumers_inherit_event_consumer():
    """
    Ensures all consumers in the app inherit from the new interface EventConsumer.
    """
    project_root = Path(__file__).parent.parent.parent / "app" / "domain"
    
    for py_file in project_root.rglob("*consumer*.py"):
        if "test" in py_file.name:
            continue
            
        content = py_file.read_text(encoding="utf-8")
        if "EventConsumer" not in content and "class" in content:
            # Maybe it doesn't define a consumer, but let's be strict
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if "Consumer" in node.name:
                            bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                            assert "EventConsumer" in bases, f"{node.name} in {py_file.name} does not inherit from EventConsumer"
            except SyntaxError:
                pass
