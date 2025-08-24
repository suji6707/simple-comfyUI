import time
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import redis
import structlog

from app.core.config import settings

logger = structlog.get_logger()
security = HTTPBearer(auto_error=False)
redis_client = redis.from_url(settings.REDIS_URL)

'''
FastAPI Depends:
- 의존성을 선언하고 FastAPI가 자동으로 주입하도록 함
- get_current_user가 인증된 유저 정보를 반환하면 current_user가 이 정보를 받음
'''
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Extract user ID from JWT token or create anonymous session.
    For demo purposes, we'll use a simple user system.
    """
    if not credentials:
        # For development, allow anonymous users
        return "anonymous"
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def rate_limit(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """
    Simple rate limiting based on user ID and IP address.
    """
    # Get client IP
    client_ip = request.client.host
    
    # Create rate limit key
    rate_limit_key = f"rate_limit:{current_user}:{client_ip}"
    
    # Determine rate limit based on user type
    if current_user == "anonymous":
        max_requests = settings.RATE_LIMIT_PER_MINUTE
    else:
        # For authenticated users, you could check premium status here
        max_requests = settings.RATE_LIMIT_PER_MINUTE
    
    current_time = int(time.time())
    window_start = current_time - 60  # 1-minute window
    
    try:
        # Use Redis sorted set to track requests in time window
        pipe = redis_client.pipeline()
        
        # Remove expired requests
        pipe.zremrangebyscore(rate_limit_key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(rate_limit_key)
        
        # Add current request
        pipe.zadd(rate_limit_key, {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(rate_limit_key, 60)
        
        results = pipe.execute()
        current_requests = results[1]
        
        if current_requests >= max_requests:
            logger.warning(
                "Rate limit exceeded",
                user_id=current_user,
                client_ip=client_ip,
                requests=current_requests,
                limit=max_requests
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {max_requests} requests per minute.",
                headers={"Retry-After": "60"}
            )
    
    except redis.RedisError as e:
        logger.error("Redis error in rate limiting", exc_info=e)
        # If Redis is down, allow request but log the error
        pass


def get_admin_user(current_user: str = Depends(get_current_user)) -> str:
    """
    Dependency to check if current user is an admin.
    For demo purposes, this is simplified.
    """
    # In production, check user roles in database
    if current_user == "admin":
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )