import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import supabase

result = supabase.table("users").select("count").execute()
print(f'DB alive: count returned {result.data[0]["count"]} users')