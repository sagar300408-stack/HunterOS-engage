import sys, os, time
sys.path.insert(0, os.getcwd())

print("Testing developer_tools import...")
t0 = time.time()
from app.developer_tools.service import simulation_state
print(f"developer_tools imported in {time.time() - t0:.2f}s")
