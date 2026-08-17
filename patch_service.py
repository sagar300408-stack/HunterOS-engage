import re
import sys

filepath = "app/domain/memory/service.py"
with open(filepath, "r") as f:
    content = f.read()

# 1. get_customer_memory
content = content.replace(
    '        include_deleted: bool = False,\n        session: AsyncSession = None,\n    ) -> Optional[CustomerMemory]:',
    '        include_deleted: bool = False,\n        session: AsyncSession = None,\n        workspace_id: Optional[UUID] = None,\n    ) -> Optional[CustomerMemory]:'
)
content = content.replace(
    '            session, customer_id, include_deleted=include_deleted\n        )',
    '            session, customer_id, include_deleted=include_deleted, workspace_id=workspace_id\n        )'
)

# 2. bulk_get_memories
content = content.replace(
    '        include_deleted: bool = False,\n        session: AsyncSession = None,\n    ) -> List[CustomerMemory]:',
    '        include_deleted: bool = False,\n        session: AsyncSession = None,\n        workspace_id: Optional[UUID] = None,\n    ) -> List[CustomerMemory]:'
)
content = content.replace(
    '            session, customer_ids, include_deleted=include_deleted\n        )',
    '            session, customer_ids, include_deleted=include_deleted, workspace_id=workspace_id\n        )'
)

# 3. get_timeline
content = content.replace(
    '        page_size: int = 50,\n        session: AsyncSession = None,\n    ) -> Tuple[List[CustomerMemoryTimelineEvent], int]:',
    '        page_size: int = 50,\n        session: AsyncSession = None,\n        workspace_id: Optional[UUID] = None,\n    ) -> Tuple[List[CustomerMemoryTimelineEvent], int]:'
)
content = content.replace(
    '            page_size=page_size,\n        )',
    '            page_size=page_size,\n            workspace_id=workspace_id,\n        )'
)

# 4. get_versions
content = content.replace(
    '        page_size: int = 50,\n        session: AsyncSession = None,\n    ) -> Tuple[List[CustomerMemoryVersion], int]:',
    '        page_size: int = 50,\n        session: AsyncSession = None,\n        workspace_id: Optional[UUID] = None,\n    ) -> Tuple[List[CustomerMemoryVersion], int]:'
)
content = content.replace(
    '            page_size=page_size,\n        )',
    '            page_size=page_size,\n            workspace_id=workspace_id,\n        )'
)

# 5. get_version_by_number
content = content.replace(
    '    async def get_version_by_number(\n        self, customer_id: UUID, version_number: int, session: AsyncSession = None\n    ) -> Optional[CustomerMemoryVersion]:',
    '    async def get_version_by_number(\n        self, customer_id: UUID, version_number: int, session: AsyncSession = None, workspace_id: Optional[UUID] = None\n    ) -> Optional[CustomerMemoryVersion]:'
)
content = content.replace(
    '            version_number=version_number,\n        )',
    '            version_number=version_number,\n            workspace_id=workspace_id,\n        )'
)

# 6. get_change_logs
content = content.replace(
    '        page_size: int = 100,\n        session: AsyncSession = None,\n    ) -> Tuple[List[MemoryChangeLog], int]:',
    '        page_size: int = 100,\n        session: AsyncSession = None,\n        workspace_id: Optional[UUID] = None,\n    ) -> Tuple[List[MemoryChangeLog], int]:'
)
content = content.replace(
    '            page_size=page_size,\n        )',
    '            page_size=page_size,\n            workspace_id=workspace_id,\n        )'
)

# 7. get_customer_memory_history
content = content.replace(
    '    async def get_customer_memory_history(\n        self, customer_id: UUID, session: AsyncSession = None\n    ) -> CustomerMemoryHistoryResponse:',
    '    async def get_customer_memory_history(\n        self, customer_id: UUID, session: AsyncSession = None, workspace_id: Optional[UUID] = None\n    ) -> CustomerMemoryHistoryResponse:'
)
content = content.replace(
    '        memory = await self._read_repo.get_by_customer_id(session, customer_id, include_deleted=True)',
    '        memory = await self._read_repo.get_by_customer_id(session, customer_id, include_deleted=True, workspace_id=workspace_id)'
)
content = content.replace(
    '        timeline_events, _ = await self._read_repo.get_timeline(session, customer_id=customer_id, page=1, page_size=50)',
    '        timeline_events, _ = await self._read_repo.get_timeline(session, customer_id=customer_id, page=1, page_size=50, workspace_id=workspace_id)'
)
content = content.replace(
    '        versions, _ = await self._read_repo.get_versions(session, customer_id=customer_id, page=1, page_size=50)',
    '        versions, _ = await self._read_repo.get_versions(session, customer_id=customer_id, page=1, page_size=50, workspace_id=workspace_id)'
)
content = content.replace(
    '        change_logs, _ = await self._read_repo.get_change_logs(session, customer_id=customer_id, page=1, page_size=100)',
    '        change_logs, _ = await self._read_repo.get_change_logs(session, customer_id=customer_id, page=1, page_size=100, workspace_id=workspace_id)'
)

with open(filepath, "w") as f:
    f.write(content)

print("Patched service!")
