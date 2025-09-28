import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """ChromaDB를 사용한 벡터 저장소 관리"""
    
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.collection_name = "yonsei_academic_papers"
    
    async def initialize(self):
        """벡터 저장소 초기화"""
        try:
            # ChromaDB 클라이언트 초기화
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # 컬렉션 생성 또는 로드
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Loaded existing collection: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Yonsei academic papers collection"}
                )
                logger.info(f"Created new collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    async def add_document(self, document: Dict[str, Any]) -> str:
        """문서를 벡터 저장소에 추가"""
        try:
            doc_id = document.get('id') or self._generate_document_id(document)
            
            # 문서 청킹 (필요한 경우)
            chunks = self._chunk_document(document)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                
                self.collection.add(
                    documents=[chunk['content']],
                    metadatas=[{
                        'title': document.get('title', ''),
                        'authors': ','.join(document.get('authors', [])),
                        'year': document.get('year', 0),
                        'source': document.get('source', ''),
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }],
                    ids=[chunk_id]
                )
            
            logger.info(f"Added document {doc_id} with {len(chunks)} chunks")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise
    
    async def similarity_search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """유사도 기반 문서 검색"""
        try:
            # ChromaDB에서 유사 문서 검색
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=filter_metadata if filter_metadata else None
            )
            
            # 결과 포맷팅
            documents = []
            for i in range(len(results['ids'][0])):
                doc = {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else 0.0,
                    'relevance_score': 1.0 - (results['distances'][0][i] if 'distances' in results else 0.0)
                }
                
                # 메타데이터에서 문서 정보 추출
                metadata = doc['metadata']
                doc.update({
                    'title': metadata.get('title', ''),
                    'authors': metadata.get('authors', '').split(',') if metadata.get('authors') else [],
                    'year': metadata.get('year', 0),
                    'source': metadata.get('source', ''),
                    'abstract': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
                })
                
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise
    
    async def get_collection_status(self) -> Dict[str, Any]:
        """컬렉션 상태 정보"""
        try:
            if not self.collection:
                return {"status": "not_initialized"}
            
            # 컬렉션 정보 조회
            count = self.collection.count()
            
            return {
                "status": "active",
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": self.persist_directory
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def delete_collection(self):
        """컬렉션 삭제"""
        try:
            if self.client and self.collection_name:
                self.client.delete_collection(name=self.collection_name)
                self.collection = None
                logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise
    
    def _generate_document_id(self, document: Dict[str, Any]) -> str:
        """문서 ID 생성"""
        import hashlib
        
        # 제목과 저자를 기반으로 해시 생성
        title = document.get('title', 'untitled')
        authors = ','.join(document.get('authors', []))
        year = str(document.get('year', ''))
        
        content_for_hash = f"{title}_{authors}_{year}"
        return hashlib.md5(content_for_hash.encode()).hexdigest()[:12]
    
    def _chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, str]]:
        """문서를 작은 청크로 분할"""
        content = document.get('content', '') or document.get('abstract', '')
        
        if not content:
            # 내용이 없으면 메타데이터로 청크 생성
            content = f"Title: {document.get('title', '')}\nAuthors: {', '.join(document.get('authors', []))}"
        
        # 간단한 청킹 로직 (실제로는 더 정교한 방법 사용 가능)
        max_chunk_size = 1000  # 1000자 단위로 분할
        
        if len(content) <= max_chunk_size:
            return [{'content': content}]
        
        chunks = []
        for i in range(0, len(content), max_chunk_size):
            chunk_content = content[i:i + max_chunk_size]
            chunks.append({'content': chunk_content})
        
        return chunks
    
    async def update_document(self, document_id: str, updated_document: Dict[str, Any]):
        """문서 업데이트"""
        try:
            # 기존 문서 삭제 후 새로 추가
            await self.delete_document(document_id)
            await self.add_document(updated_document)
            
        except Exception as e:
            logger.error(f"Failed to update document {document_id}: {e}")
            raise
    
    async def delete_document(self, document_id: str):
        """문서 삭제"""
        try:
            # 해당 문서의 모든 청크 찾기
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise
    
    async def search_by_metadata(self, metadata_filter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """메타데이터 기반 검색"""
        try:
            results = self.collection.get(
                where=metadata_filter,
                include=['documents', 'metadatas']
            )
            
            documents = []
            for i in range(len(results['ids'])):
                doc = {
                    'id': results['ids'][i],
                    'content': results['documents'][i],
                    'metadata': results['metadatas'][i]
                }
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            raise