# retreival-service/data 디렉터리

- Sqlite3 DB에 메타데이터와 벡터 임베딩 보관
- 실제 벡터 검색은 FAISS 인덱스에서 찾고 -> Sqlite3 DB에서 정보 확인하는 방식으로 이루어짐
- 벡터 인덱스 구축 스크립트
- 실제 데이터는 git에 안 올라감
