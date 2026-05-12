from supabase._async.client import AsyncClient, create_client
from app.config import settings

_supabase_client: AsyncClient | None = None
 
async def get_supabase() -> AsyncClient:
    global _supabase_client
    
    
    if _supabase_client is None:
        _supabase_client = await create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        
    
    return _supabase_client