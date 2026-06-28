from datetime import datetime, timezone, timedelta
from app.config import get_settings

class SystemClock:
    @staticmethod
    def now() -> datetime:
        """
        Return the current UTC time.
        If developer tools are enabled and a time machine offset is active,
        returns the shifted time.
        """
        base_time = datetime.now(timezone.utc)
        settings = get_settings()
        if settings.enable_developer_tools:
            try:
                from app.developer_tools.service import simulation_state
                if simulation_state.time_offset_seconds > 0:
                    return base_time + timedelta(seconds=simulation_state.time_offset_seconds)
            except ImportError:
                pass
        return base_time
