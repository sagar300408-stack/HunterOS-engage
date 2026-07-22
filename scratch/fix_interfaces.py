import os
import re

files_to_fix = [
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\collaboration\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\context\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\impact\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\onboarding\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\ui\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\intelligence\consumer.py"
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace imports
        content = content.replace("from app.events.bus.event_bus import EventConsumer, HunterEvent", "from app.events.bus.interfaces import EventConsumer\nfrom app.events.model.base_event import UniversalBaseEvent\nfrom typing import List")
        content = content.replace("from app.events.bus.event_bus import EventConsumer", "from app.events.bus.interfaces import EventConsumer\nfrom typing import List")
        
        # Replace @property def priority with def get_priority
        content = re.sub(r"@property\s*\n\s*def priority\(self\) -> int:", "def get_priority(self) -> int:", content)
        
        # Replace process with handle_event and HunterEvent with UniversalBaseEvent
        content = re.sub(r"async def process\(self, event:[^)]+\) -> None:", "async def handle_event(self, event: UniversalBaseEvent) -> None:", content)

        # Add get_subscriptions if not present
        if "def get_subscriptions" not in content:
            # We can insert get_subscriptions right before get_priority or handle_event
            if "def get_priority" in content:
                content = content.replace("def get_priority(self) -> int:", "def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:\n        return [UniversalBaseEvent]\n\n    def get_priority(self) -> int:")
            elif "async def handle_event" in content:
                content = content.replace("async def handle_event", "def get_subscriptions(self) -> List[type[UniversalBaseEvent]]:\n        return [UniversalBaseEvent]\n\n    async def handle_event")

        # Replace event.type with getattr(event, "event_name", "") or similar?
        # Actually in HunterOS, UniversalBaseEvent has `event_name`
        content = content.replace("event.type.startswith", "getattr(event, 'event_name', '').startswith")
        content = content.replace("event.type ==", "getattr(event, 'event_name', '') ==")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {filepath}")
    else:
        print(f"Not found: {filepath}")
