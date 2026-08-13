import re
import os

path = 'tests/domain/operations/orchestration/test_orchestration_engine.py'
content = open(path).read()

# 1. Replace make_action
old_make_action = """def make_action(
    workspace_id,
    action_id,
    status=ActionStatus.APPROVED,
    revision_id="rev-pinned-001",
):
    action = MagicMock(spec=Action)
    action.id = action_id
    action.workspace_id = workspace_id
    action.status = status
    action.revision_id = revision_id
    action.version_number = 2
    action.action_type = ActionType.CREATE_FOLLOWUP
    action.execution_metadata = {}
    action.advance_revision = MagicMock()
    return action"""

new_make_action = """def make_action(
    workspace_id,
    action_id,
    status=ActionStatus.APPROVED,
    revision_id="rev-pinned-001",
):
    action = Action()
    action.id = action_id
    action.workspace_id = workspace_id
    action.status = status
    action.revision_id = revision_id
    action.version_number = 2
    action.action_type = ActionType.CREATE_FOLLOWUP
    action.execution_metadata = {}
    action.advance_revision = MagicMock()
    return action"""

content = content.replace(old_make_action, new_make_action)

# 2. Replace make_orchestration_run
old_make_run = """def make_orchestration_run(workspace_id, action_id, state=OrchestrationRunState.EXECUTING, action_version=2):
    run = MagicMock(spec=OrchestrationRun)
    run.workspace_id = workspace_id
    run.action_id = action_id
    run.state = state
    run.action_version = action_version
    run.attempt_count = 1
    run.max_attempts = 3
    
    attempt = MagicMock(spec=OrchestrationAttempt)
    attempt.attempt_number = 1
    attempt.state = OrchestrationAttemptState.EXECUTING
    
    run.attempts = [attempt]
    return run"""

new_make_run = """def make_orchestration_run(workspace_id, action_id, state=OrchestrationRunState.EXECUTING, action_version=2):
    run = OrchestrationRun(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        action_id=action_id,
        state=state,
        action_version=action_version,
        attempt_count=1,
        max_attempts=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    attempt = OrchestrationAttempt(
        id=uuid.uuid4(),
        run_id=run.id,
        attempt_number=1,
        state=OrchestrationAttemptState.EXECUTING,
        started_at=datetime.now(timezone.utc)
    )
    
    run.attempts = [attempt]
    return run"""

content = content.replace(old_make_run, new_make_run)

# 3. Add mock_add logic
lines = content.split('\n')
new_lines = []
for i, line in enumerate(lines):
    if line.strip() == 'session = AsyncMock()':
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(line)
        if i + 1 < len(lines) and 'mock_result =' in lines[i+1]:
            mock_add = f'''{indent}def mock_add(obj):
{indent}    import uuid
{indent}    from datetime import datetime, timezone
{indent}    if not getattr(obj, "id", None): obj.id = uuid.uuid4()
{indent}    if hasattr(obj, "run") and getattr(obj, "run", None): obj.run_id = obj.run.id
{indent}    if hasattr(obj, "started_at") and not getattr(obj, "started_at", None): obj.started_at = datetime.now(timezone.utc)
{indent}    if hasattr(obj, "created_at") and not getattr(obj, "created_at", None): obj.created_at = datetime.now(timezone.utc)
{indent}    if hasattr(obj, "updated_at") and not getattr(obj, "updated_at", None): obj.updated_at = datetime.now(timezone.utc)
{indent}session.add = MagicMock(side_effect=mock_add)
{indent}session.commit = AsyncMock()'''
            new_lines.append(mock_add)
    else:
        new_lines.append(line)

open(path, 'w').write('\n'.join(new_lines))
