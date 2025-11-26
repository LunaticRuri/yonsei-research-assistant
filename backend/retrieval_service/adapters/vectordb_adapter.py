from typing import List
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import sqlite3
import logging

from retrieval_service.adapters.base_adapters import BaseRetriever
from retrieval_service.scrapers.search_params import VectorSearchParams
from retrieval_service.config import settings
from shared.models import Document, SearchRequest, QueryOperator, RetrievalRoute



class VectorDBAdapter(BaseRetriever):
    """FAISS 기반 Vector DB 어댑터"""
    
    def __init__(self):
        
        self.is_faiss_initialized = True
        self.index = None
        self.metadata_faiss_map = None
        self.sqlite_connection = None

        try:
            self.index = faiss.read_index(settings.FAISS_INDEX_PATH)
            
            with open(settings.FAISS_ID_TO_METADATA_PATH, 'rb') as f:
                self.metadata_faiss_map = pickle.load(f)
            
            self.sqlite_connection = sqlite3.connect(settings.METADATA_DB_PATH)

        except FileNotFoundError:
            logging.warning("FAISS ID to Metadata 매핑 파일을 찾을 수 없습니다. 메타데이터 조회가 불가능합니다.")
            self.is_faiss_initialized = False
        except Exception as e:
            logging.error(f"FAISS 인덱스 로드 중 오류 발생: {e}")
            self.is_faiss_initialized = False
        
        self.encoder = SentenceTransformer(settings.VECTOR_EMBEDDING_MODEL)
        self.logger = logging.getLogger(__name__)
    
    async def request_to_search_params(self, request: SearchRequest) -> VectorSearchParams:
        """
        SearchRequest를 어댑터별 검색 파라미터 객체로 변환
        Vector DB는 별도의 검색 파라미터 객체가 없으므로 주어진 검색 쿼리를 적절히 임베딩 벡터로 변환한 후,
        VectorSearchParams 객체를 생성하여 반환.
        
        Args:
            request (SearchRequest): 통합 검색 요청 객체
        Returns:
            VectorSearchParams: Vector DB 검색 파라미터 객체
        """
        queries = request.queries
        filters = request.filters

        query_1 = queries.query_1
        
        
        query_2 = None
        vector_2 = None
        query_3 = None
        vector_3 = None

        year_range = None

        # Query 2, 3이 존재하고 NOT 연산자가 아닐 경우에만 벡터 생성
        if queries.query_2:
            if queries.operator_1 is QueryOperator.AND:
                query_1 += " " + queries.query_2
            if queries.operator_1 is QueryOperator.OR:
                query_2 = queries.query_2
                
        if queries.query_3:
            if queries.operator_2 is QueryOperator.AND:
                query_1 += " " + queries.query_3
            if queries.operator_2 is QueryOperator.OR:
                if not query_2:
                    query_2 = queries.query_3
                else:
                    query_3 = queries.query_3

        vector_1 = np.array(self.encoder.encode([query_1], show_progress_bar=False), dtype='float32') if query_1 else None
        vector_2 = np.array(self.encoder.encode([query_2], show_progress_bar=False), dtype='float32') if query_2 else None
        vector_3 = np.array(self.encoder.encode([query_3], show_progress_bar=False), dtype='float32') if query_3 else None

        # Vector DB의 경우 필터는 year_range 밖에 없음.
        if filters.get("year_range"):
            from_year, to_year = filters["year_range"]
            year_range = {"from_year": from_year, "to_year": to_year}

        return VectorSearchParams(
            query_1=query_1,
            vector_1=vector_1,
            query_2=query_2,
            vector_2=vector_2,
            query_3=query_3,
            vector_3=vector_3,
            year_range=year_range
        )


    async def search(
        self, 
        search_params: VectorSearchParams,
        top_k: int = 10
    ) -> List[Document]:
        """
        벡터 유사도 검색
        """
        if not self.is_faiss_initialized:
            self.logger.error("FAISS 인덱스가 초기화되지 않았습니다.")
            return []
        try:
            retrieved_faiss_ids = set()
            
            # Query 1 FAISS 검색 (top_k * 2로 오버페칭)
            distances_1, faiss_ids_1 = self.index.search(search_params.vector_1, top_k * 2)

            if faiss_ids_1.size != 0 and faiss_ids_1[0][0] != -1:
                retrieved_faiss_ids.update(faiss_ids_1[0])

            # Query 2 FAISS 검색
            if search_params.vector_2 is not None:
                distances_2, faiss_ids_2 = self.index.search(search_params.vector_2, top_k * 2)
                if faiss_ids_2.size != 0 and faiss_ids_2[0][0] != -1:
                    retrieved_faiss_ids.update(faiss_ids_2[0])
            
            # Query 3 FAISS 검색
            if search_params.vector_3 is not None:
                distances_3, faiss_ids_3 = self.index.search(search_params.vector_3, top_k * 2)
                if faiss_ids_3.size != 0 and faiss_ids_3[0][0] != -1:
                    retrieved_faiss_ids.update(faiss_ids_3[0])
            
            # faiss_id를 메타데이터 ID(ISBN)로 변환
            retrieved_isbn_id_tuples = [self.metadata_faiss_map[i] for i in retrieved_faiss_ids if i in self.metadata_faiss_map]
            retrieved_isbns = list(set([isbn for isbn, chunk_index in retrieved_isbn_id_tuples]))

            # SQLite에서 최종 정보 조회 (필터 적용)
            if not retrieved_isbns:
                return []
            
            placeholders = ','.join('?' for _ in retrieved_isbns)
            
            if search_params.year_range:
                from_year = search_params.year_range.from_year
                to_year = search_params.year_range.to_year
                sql = f"""
                    SELECT isbn, title, publication_year, intro, toc, nlk_subjects 
                    FROM book_metadata
                    WHERE isbn IN ({placeholders}) 
                    AND ((publication_year BETWEEN ? AND ?) or (publication_year = 0))
                """
                params = retrieved_isbns + [from_year, to_year]
            else:
                placeholders = ','.join('?' for _ in retrieved_isbns)
                sql = f"""
                    SELECT isbn, title, publication_year, intro, toc, nlk_subjects 
                    FROM book_metadata
                    WHERE isbn IN ({placeholders})
                """
                params = retrieved_isbns
            
            cur = self.sqlite_connection.cursor()
            cur.execute(sql, params)
            results = cur.fetchall()
            self.sqlite_connection.close()

            documents = []
            for isbn, title, publication_year, intro, toc, subjects in results:
                doc = Document(
                    content=title + "\n\n" + intro + "\n\n" + toc,
                    metadata={
                        'source': RetrievalRoute.VECTOR_DB.value,
                        'title': title,
                        'publication_year': publication_year,
                        'nlk_subjects': subjects
                    },
                    score=1.0, # 초기 점수는 1.0으로 설정
                    doc_id=isbn
                )
                documents.append(doc)
                
                if len(documents) >= top_k:
                    break
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    async def health_check(self) -> bool:
        """FAISS 인덱스 상태 확인"""
        try:
            return self.index.ntotal > 0
        except:
            return False
    
    @property
    def source_name(self) -> str:
        return "vector_db"