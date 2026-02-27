from fastapi import Header, HTTPException, status
import os
from dotenv import load_dotenv

load_dotenv()
INTERNAL_SECRET = os.getenv("INTERNAL_API_KEY", "arthik-internal-agent-secret-key")

async def verify_internal_key(x_internal_key: str = Header(..., alias="X-Internal-Key")):
    if x_internal_key != INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid Internal API Key"
        )
