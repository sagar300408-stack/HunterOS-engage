import pytest
from app.domain.operations.models import ActionStatus
from app.domain.operations.planning.policy import DependencySatisfactionPolicy

def test_is_satisfied():
    assert DependencySatisfactionPolicy.is_satisfied(ActionStatus.COMPLETED) is True
    assert DependencySatisfactionPolicy.is_satisfied(ActionStatus.PLANNED) is False
    assert DependencySatisfactionPolicy.is_satisfied(ActionStatus.EXECUTING) is False
    assert DependencySatisfactionPolicy.is_satisfied(ActionStatus.FAILED) is False

def test_is_permanently_failed():
    assert DependencySatisfactionPolicy.is_permanently_failed(ActionStatus.FAILED) is True
    assert DependencySatisfactionPolicy.is_permanently_failed(ActionStatus.CANCELLED) is True
    assert DependencySatisfactionPolicy.is_permanently_failed(ActionStatus.REJECTED) is True
    assert DependencySatisfactionPolicy.is_permanently_failed(ActionStatus.EXPIRED) is True
    assert DependencySatisfactionPolicy.is_permanently_failed(ActionStatus.PLANNED) is False
    assert DependencySatisfactionPolicy.is_permanently_failed(ActionStatus.EXECUTING) is False
    assert DependencySatisfactionPolicy.is_permanently_failed(ActionStatus.COMPLETED) is False
