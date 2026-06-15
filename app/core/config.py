from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'smart_classroom_v2.db'}"
PROJECT_NAME = "Smart Classroom AI Monitoring V2"
