import redis
import os

# Docker 환경에서는 서비스 이름('redis')이 호스트 이름이 됩니다.
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    # Redis 연결 풀을 생성합니다. 이렇게 하면 매번 연결을 새로 맺지 않아 효율적입니다.
    redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    redis_conn = redis.Redis(connection_pool=redis_pool)
    # 연결 테스트
    redis_conn.ping()
    print("✅ Redis에 성공적으로 연결되었습니다.")
except redis.exceptions.ConnectionError as e:
    print(f"❌ Redis 연결에 실패했습니다: {e}")
    redis_conn = None

def get_redis_connection():
    """Redis 연결 객체를 반환하는 함수"""
    if not redis_conn:
        raise ConnectionError("Redis is not connected.")
    return redis_conn