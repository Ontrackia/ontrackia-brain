import os
from typing import Optional
from dotenv import load_dotenv

# Load .env - try multiple paths
load_dotenv()  # Current directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# Basic environment config
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "aerobrain_docs")
SQLITE_PATH: str = os.getenv("AEROBRAIN_SQLITE_PATH", "data/failures.db")

OPENAI_MODEL_CHAT: str = os.getenv("OPENAI_MODEL_CHAT", "gpt-4o-mini")
OPENAI_MODEL_VISION: str = os.getenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
OPENAI_MODEL_STT: str = os.getenv("OPENAI_MODEL_STT", "whisper-1")

RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
RAG_MIN_SCORE: float = float(os.getenv("RAG_MIN_SCORE", "0.3"))

SAFETY_DISCLAIMER: str = (
    "This information is advisory only. Always verify with OEM manuals, MMEL/MEL, AMM, SRM, "
    "and approved organisational procedures before performing or certifying any work."
)

# Debug
if OPENAI_API_KEY:
    print(f"[CONFIG] API key loaded: {OPENAI_API_KEY[:15]}...")
else:
    print("[CONFIG] WARNING: OPENAI_API_KEY not found!")

    

      

    
