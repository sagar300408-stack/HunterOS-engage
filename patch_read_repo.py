import re
import sys

filepath = "app/domain/memory/repositories/read_repository.py"
with open(filepath, "r") as f:
    content = f.read()

# 1. get_by_customer_id
content = content.replace(
    '        include_deleted: bool = kwargs.get("include_deleted", False)',
    '        include_deleted: bool = kwargs.get("include_deleted", False)\n        workspace_id: Optional[UUID] = kwargs.get("workspace_id")'
)
content = content.replace(
    '            if not include_deleted:',
    '            if workspace_id:\n                stmt = stmt.where(CustomerMemory.workspace_id == workspace_id)\n            if not include_deleted:'
)

# 2. get_by_id
content = content.replace(
    '        memory_id: Optional[UUID] = kwargs.get("memory_id")\n        include_deleted: bool = kwargs.get("include_deleted", False)',
    '        memory_id: Optional[UUID] = kwargs.get("memory_id")\n        include_deleted: bool = kwargs.get("include_deleted", False)\n        workspace_id: Optional[UUID] = kwargs.get("workspace_id")'
)

content = content.replace(
    '            stmt = select(CustomerMemory).where(CustomerMemory.id == memory_id)',
    '            stmt = select(CustomerMemory).where(CustomerMemory.id == memory_id)\n            if workspace_id:\n                stmt = stmt.where(CustomerMemory.workspace_id == workspace_id)'
)

# 3. get_timeline
content = content.replace(
    '        page_size: int = kwargs.get("page_size", 50)',
    '        page_size: int = kwargs.get("page_size", 50)\n        workspace_id: Optional[UUID] = kwargs.get("workspace_id")'
)

content = content.replace(
    '            stmt = select(CustomerMemoryTimelineEvent).where(\n                CustomerMemoryTimelineEvent.customer_id == customer_id\n            )',
    '            stmt = select(CustomerMemoryTimelineEvent).where(\n                CustomerMemoryTimelineEvent.customer_id == customer_id\n            )\n            if workspace_id:\n                stmt = stmt.join(CustomerMemory, CustomerMemory.customer_id == CustomerMemoryTimelineEvent.customer_id).where(CustomerMemory.workspace_id == workspace_id)'
)

# 4. get_versions
content = content.replace(
    '        page_size: int = kwargs.get("page_size", 50)',
    '        page_size: int = kwargs.get("page_size", 50)\n        workspace_id: Optional[UUID] = kwargs.get("workspace_id")'
)

content = content.replace(
    '            stmt = select(CustomerMemoryVersion).where(CustomerMemoryVersion.customer_id == customer_id)',
    '            stmt = select(CustomerMemoryVersion).where(CustomerMemoryVersion.customer_id == customer_id)\n            if workspace_id:\n                stmt = stmt.join(CustomerMemory, CustomerMemory.customer_id == CustomerMemoryVersion.customer_id).where(CustomerMemory.workspace_id == workspace_id)'
)

# 5. get_version_by_number
content = content.replace(
    '        version_number: Optional[int] = kwargs.get("version_number")',
    '        version_number: Optional[int] = kwargs.get("version_number")\n        workspace_id: Optional[UUID] = kwargs.get("workspace_id")'
)

content = content.replace(
    '            stmt = select(CustomerMemoryVersion).where(\n                CustomerMemoryVersion.customer_id == customer_id,\n                CustomerMemoryVersion.version_number == version_number,\n            )',
    '            stmt = select(CustomerMemoryVersion).where(\n                CustomerMemoryVersion.customer_id == customer_id,\n                CustomerMemoryVersion.version_number == version_number,\n            )\n            if workspace_id:\n                stmt = stmt.join(CustomerMemory, CustomerMemory.customer_id == CustomerMemoryVersion.customer_id).where(CustomerMemory.workspace_id == workspace_id)'
)

# 6. get_change_logs
content = content.replace(
    '        page_size: int = kwargs.get("page_size", 50)',
    '        page_size: int = kwargs.get("page_size", 50)\n        workspace_id: Optional[UUID] = kwargs.get("workspace_id")'
)

content = content.replace(
    '            stmt = select(MemoryChangeLog).where(MemoryChangeLog.customer_id == customer_id)',
    '            stmt = select(MemoryChangeLog).where(MemoryChangeLog.customer_id == customer_id)\n            if workspace_id:\n                stmt = stmt.join(CustomerMemory, CustomerMemory.customer_id == MemoryChangeLog.customer_id).where(CustomerMemory.workspace_id == workspace_id)'
)

with open(filepath, "w") as f:
    f.write(content)

print("Patched read repository!")
