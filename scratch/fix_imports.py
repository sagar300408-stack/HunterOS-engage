import os

files_to_fix = [
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\collaboration\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\context\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\impact\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\intelligence\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\onboarding\consumer.py",
    r"c:\Users\acer\OneDrive\Documents\GitHub\HunterOS engage\app\domain\ui\consumer.py"
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace("from app.integrations.postgres.database import SessionLocal", "from app.integrations.postgres.database import get_session")
        content = content.replace("async with SessionLocal() as session:", "async with get_session() as session:")
        content = content.replace("from app.events.model.event import UniversalBaseEvent", "from app.events.model.base_event import UniversalBaseEvent")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {filepath}")
    else:
        print(f"Not found: {filepath}")
