from uuid import UUID

class Policy:
    def __init__(self, workspace_id: UUID):
        self.workspace_id = workspace_id
        
    def effective_max_attempts(self, buying_stage: str = None) -> int:
        if buying_stage == "Purchase Ready":
            return 5
        elif buying_stage == "Research":
            return 2
        return 3

def get_workspace_policy(workspace_id: UUID) -> Policy:
    # Stub: load from DB in a real app
    return Policy(workspace_id)
