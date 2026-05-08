import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scheduler import run_monthly_job

if __name__ == "__main__":
	run_monthly_job()