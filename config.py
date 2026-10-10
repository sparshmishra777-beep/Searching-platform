import os
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass
DB_PATH = os.getenv("DB_PATH", "intel.db")
TIMEOUT = 15
RETRIES = 3
MATCH_WEIGHTS = {"industry": 0.30, "stage": 0.20, "geography": 0.15, "check": 0.20, "similarity": 0.15}
DATA_GOV_IN_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
MCA_MAX_SCAN_PAGES = int(os.getenv("MCA_MAX_SCAN_PAGES", "5"))
