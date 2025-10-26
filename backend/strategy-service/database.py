import redis
# [삭제] import os <-- 더 이상 사용하지 않습니다.
from .config import settings  # <--- [추가!] config.py에서 settings를 임포트합니다.

# [삭제] REDIS_HOST = os.getenv("REDIS_HOST", "redis")
# [삭제] REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    # Redis 연결 풀을 생성합니다.
    # [변경] os.getenv 대신 config.py의 settings 객체를 사용합니다.
    redis_pool = redis.ConnectionPool(
        host=settings.REDIS_HOST, 
        port=settings.REDIS_PORT, 
        db=0, 
        decode_responses=True
    )
    redis_conn = redis.Redis(connection_pool=redis_pool)
    
    # 연결 테스트
    redis_conn.ping()
    
    # [변경] 디버깅을 위해 실제 연결된 호스트 정보 출력
    print(f"✅ Redis에 성공적으로 연결되었습니다. (Host: {settings.REDIS_HOST}:{settings.REDIS_PORT})")

except redis.exceptions.ConnectionError as e:
    # [변경] 연결 실패 시에도 어떤 호스트로 시도했는지 출력
    print(f"❌ Redis 연결에 실패했습니다 (Host: {settings.REDIS_HOST}:{settings.REDIS_PORT}): {e}")
    redis_conn = None

def get_redis_connection():
    """Redis 연결 객체를 반환하는 함수"""
    if not redis_conn:
        # [변경] 에러 메시지를 좀 더 명확하게
        raise ConnectionError(
            f"Redis is not connected. (Failed to connect to {settings.REDIS_HOST}:{settings.REDIS_PORT} on startup)"
        )
    return redis_conn