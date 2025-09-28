from typing import List, Dict, Any
from shared.models import SearchStrategy, RAGAnalysisResponse, DocumentResult
from .vector_store import VectorStoreManager
from .document_processor import DocumentProcessor
import logging

logger = logging.getLogger(__name__)

class RAGEngine:
    """RAG(검색 증강 생성) 엔진의 핵심 로직"""
    
    def __init__(self, vector_store: VectorStoreManager, document_processor: DocumentProcessor):
        self.vector_store = vector_store
        self.document_processor = document_processor
        self.analysis_cache = {}  # 분석 결과 캐싱
    
    async def analyze_documents(
        self,
        search_strategy: SearchStrategy,
        session_id: str,
        analysis_depth: str = "standard"
    ) -> RAGAnalysisResponse:
        """검색 전략을 바탕으로 문서 분석 수행"""
        
        try:
            # 1. 벡터 검색 수행
            relevant_documents = await self._retrieve_relevant_documents(search_strategy)
            
            # 2. 문서 분석
            analysis_results = await self._analyze_retrieved_documents(
                relevant_documents, search_strategy, analysis_depth
            )
            
            # 3. 핵심 논쟁 지점 추출
            key_debates = await self._extract_key_debates(analysis_results)
            
            # 4. 문헌 메타데이터 생성
            document_metadata = await self._generate_document_metadata(relevant_documents)
            
            # 5. 분석 신뢰도 평가
            confidence_score = self._calculate_analysis_confidence(
                len(relevant_documents), analysis_results
            )
            
            return RAGAnalysisResponse(
                session_id=session_id,
                analysis_summary=analysis_results["summary"],
                key_debates=key_debates,
                relevant_documents=document_metadata,
                confidence_score=confidence_score,
                search_strategy_used=search_strategy,
                analysis_limitations=self._generate_limitations_note(relevant_documents)
            )
        
        except Exception as e:
            logger.error(f"RAG analysis failed: {e}")
            raise
    
    async def _retrieve_relevant_documents(self, search_strategy: SearchStrategy) -> List[Dict]:
        """검색 전략을 바탕으로 관련 문서 검색"""
        
        # 주요 키워드를 조합하여 쿼리 생성
        query_text = " ".join(search_strategy.primary_keywords)
        
        # 벡터 유사도 검색
        similar_documents = await self.vector_store.similarity_search(
            query=query_text,
            limit=50,  # 충분한 수의 문서 검색
            filter_metadata={"academic_field": search_strategy.academic_fields}
        )
        
        # 확장 키워드로 추가 검색
        if search_strategy.expansion_keywords:
            expansion_query = " ".join(search_strategy.expansion_keywords[:3])
            additional_docs = await self.vector_store.similarity_search(
                query=expansion_query,
                limit=20
            )
            similar_documents.extend(additional_docs)
        
        # 중복 제거 및 관련성 점수로 정렬
        unique_docs = self._deduplicate_documents(similar_documents)
        return sorted(unique_docs, key=lambda x: x.get('relevance_score', 0), reverse=True)[:20]
    
    async def _analyze_retrieved_documents(
        self,
        documents: List[Dict],
        search_strategy: SearchStrategy,
        depth: str
    ) -> Dict[str, Any]:
        """검색된 문서들에 대한 분석 수행"""
        
        analysis = {
            "summary": "",
            "themes": [],
            "methodologies": [],
            "findings": [],
            "gaps": []
        }
        
        if depth == "detailed":
            # 상세 분석 로직
            analysis = await self._perform_detailed_analysis(documents, search_strategy)
        else:
            # 표준 분석 로직
            analysis = await self._perform_standard_analysis(documents, search_strategy)
        
        return analysis
    
    async def _perform_standard_analysis(
        self,
        documents: List[Dict],
        search_strategy: SearchStrategy
    ) -> Dict[str, Any]:
        """표준 수준의 문서 분석"""
        
        # 문서 내용 추출
        document_contents = [doc.get('content', '') for doc in documents]
        
        # 주요 테마 추출 (키워드 기반)
        themes = self._extract_themes(document_contents, search_strategy.primary_keywords)
        
        # 연구 방법론 분석
        methodologies = self._analyze_methodologies(document_contents)
        
        # 주요 발견사항 요약
        findings = self._summarize_findings(document_contents)
        
        # 연구 공백 식별
        gaps = self._identify_research_gaps(document_contents, search_strategy)
        
        # 전체 요약 생성
        summary = self._generate_analysis_summary(themes, methodologies, findings)
        
        return {
            "summary": summary,
            "themes": themes,
            "methodologies": methodologies,
            "findings": findings,
            "gaps": gaps
        }
    
    async def _perform_detailed_analysis(
        self,
        documents: List[Dict],
        search_strategy: SearchStrategy
    ) -> Dict[str, Any]:
        """상세 수준의 문서 분석 (LLM 활용)"""
        
        # TODO: LLM을 활용한 더 정교한 분석 로직
        # 현재는 표준 분석과 동일하게 처리
        return await self._perform_standard_analysis(documents, search_strategy)
    
    async def _extract_key_debates(self, analysis_results: Dict[str, Any]) -> List[Dict[str, str]]:
        """핵심 논쟁 지점 추출"""
        
        debates = []
        
        # 테마에서 상반된 관점 찾기
        for theme in analysis_results.get("themes", []):
            if self._contains_contrasting_views(theme):
                debates.append({
                    "topic": theme["name"],
                    "description": theme["controversy"],
                    "positions": theme.get("different_positions", [])
                })
        
        # 연구 방법론의 차이점
        methodologies = analysis_results.get("methodologies", [])
        if len(set(methodologies)) > 1:
            debates.append({
                "topic": "연구 방법론적 접근",
                "description": "연구자들이 서로 다른 방법론적 접근을 사용하고 있습니다.",
                "positions": list(set(methodologies))
            })
        
        return debates[:5]  # 최대 5개의 주요 논쟁점
    
    async def _generate_document_metadata(self, documents: List[Dict]) -> List[DocumentResult]:
        """문서 메타데이터 생성"""
        
        metadata_list = []
        
        for doc in documents[:10]:  # 상위 10개 문서만
            # 연세대 도서관 소장 여부 확인 (Mock)
            availability = await self._check_yonsei_library_availability(doc)
            
            metadata = DocumentResult(
                title=doc.get('title', 'Unknown Title'),
                authors=doc.get('authors', []),
                publication_year=doc.get('year', 0),
                source=doc.get('source', 'Unknown Source'),
                abstract=doc.get('abstract', '')[:200] + "...",
                relevance_score=doc.get('relevance_score', 0.0),
                yonsei_library_status=availability,
                yonsei_access_link=doc.get('access_link', '')
            )
            
            metadata_list.append(metadata)
        
        return metadata_list
    
    async def _check_yonsei_library_availability(self, document: Dict) -> str:
        """연세대 도서관 소장 여부 확인 (Mock 구현)"""
        # TODO: 실제 도서관 API 연동
        import random
        statuses = [
            "✅ 전자 저널 원문 이용 가능",
            "📚 중앙도서관 대출 가능",
            "📜 dCollection에서 원문 이용 가능",
            "❌ 소장하지 않음"
        ]
        return random.choice(statuses)
    
    def _calculate_analysis_confidence(self, doc_count: int, analysis: Dict) -> float:
        """분석 신뢰도 계산"""
        base_confidence = 0.6
        
        # 문서 수에 따른 가중치
        doc_weight = min(doc_count * 0.02, 0.3)
        
        # 분석 결과 완성도에 따른 가중치
        completeness_weight = len(analysis.get("themes", [])) * 0.05
        
        return min(base_confidence + doc_weight + completeness_weight, 0.95)
    
    def _generate_limitations_note(self, documents: List[Dict]) -> str:
        """분석 제한사항 안내문 생성"""
        return f"""
        이 분석은 제한된 샘플 데이터셋({len(documents)}개 문서)을 바탕으로 한 예비 분석입니다.
        
        주요 제한사항:
        1. 전체 학술 데이터베이스가 아닌 부분적 샘플 기반
        2. 최신 연구 동향이 완전히 반영되지 않을 수 있음
        3. 언어적 편향 가능성 (한국어/영어 문헌 위주)
        
        보다 포괄적인 검색을 위해서는 실제 도서관 검색을 수행하시기 바랍니다.
        """
    
    # 헬퍼 메서드들
    def _deduplicate_documents(self, documents: List[Dict]) -> List[Dict]:
        """문서 중복 제거"""
        seen_titles = set()
        unique_docs = []
        
        for doc in documents:
            title = doc.get('title', '')
            if title not in seen_titles:
                seen_titles.add(title)
                unique_docs.append(doc)
        
        return unique_docs
    
    def _extract_themes(self, contents: List[str], keywords: List[str]) -> List[Dict]:
        """키워드 기반 주제 추출"""
        # 간단한 키워드 매칭 기반 테마 추출
        themes = []
        for keyword in keywords:
            mention_count = sum(1 for content in contents if keyword in content)
            if mention_count > 2:
                themes.append({
                    "name": keyword,
                    "frequency": mention_count,
                    "description": f"'{keyword}' 관련 연구 동향"
                })
        
        return themes
    
    def _analyze_methodologies(self, contents: List[str]) -> List[str]:
        """연구 방법론 분석"""
        methodologies = set()
        method_keywords = {
            "설문조사": ["설문", "survey", "questionnaire"],
            "실험연구": ["실험", "experiment", "실험군"],
            "질적연구": ["인터뷰", "interview", "질적"],
            "양적연구": ["통계", "회귀분석", "상관분석"],
            "문헌연구": ["문헌", "리뷰", "메타분석"]
        }
        
        for content in contents:
            for method, keywords in method_keywords.items():
                if any(kw in content for kw in keywords):
                    methodologies.add(method)
        
        return list(methodologies)
    
    def _summarize_findings(self, contents: List[str]) -> List[str]:
        """주요 발견사항 요약"""
        # 간단한 발견사항 추출 로직
        findings = []
        finding_indicators = ["결과", "발견", "나타났다", "확인되었다"]
        
        for content in contents:
            sentences = content.split('.')
            for sentence in sentences:
                if any(indicator in sentence for indicator in finding_indicators):
                    findings.append(sentence.strip())
                    if len(findings) >= 5:
                        break
        
        return findings[:5]
    
    def _identify_research_gaps(self, contents: List[str], strategy: SearchStrategy) -> List[str]:
        """연구 공백 식별"""
        gaps = []
        
        # 키워드 조합에서 누락된 부분 찾기
        all_keywords = strategy.primary_keywords + strategy.expansion_keywords
        
        # 간단한 공백 식별 로직
        if len(all_keywords) > 2:
            gaps.append("키워드 간 상호작용 효과에 대한 연구 부족")
        
        gaps.append("한국적 맥락에서의 연구 필요")
        gaps.append("최신 기술 동향 반영 연구 부족")
        
        return gaps[:3]
    
    def _generate_analysis_summary(self, themes: List[Dict], methodologies: List[str], findings: List[str]) -> str:
        """전체 분석 요약 생성"""
        theme_names = [theme["name"] for theme in themes]
        
        summary = f"""
        검색된 문헌들을 분석한 결과, 주요 연구 주제는 {', '.join(theme_names[:3])} 등으로 나타났습니다.
        
        연구 방법론적으로는 {', '.join(methodologies[:3])} 등의 접근이 주로 사용되었으며,
        
        주요 발견사항으로는 다음과 같은 내용들이 확인되었습니다:
        {chr(10).join(['- ' + finding[:100] + '...' for finding in findings[:3]])}
        """
        
        return summary.strip()
    
    def _contains_contrasting_views(self, theme: Dict) -> bool:
        """테마에 상반된 관점이 포함되어 있는지 확인"""
        # 간단한 논쟁 판단 로직
        controversial_keywords = ["반면", "그러나", "하지만", "대조적으로", "상반된"]
        description = theme.get("description", "")
        
        return any(kw in description for kw in controversial_keywords)
    
    async def ingest_documents(self, documents: List[Dict]) -> Dict[str, Any]:
        """새로운 문서들을 시스템에 추가"""
        
        processed_count = 0
        
        for doc in documents:
            try:
                # 문서 전처리
                processed_doc = await self.document_processor.process_document(doc)
                
                # 벡터 저장소에 추가
                await self.vector_store.add_document(processed_doc)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to ingest document {doc.get('title', 'Unknown')}: {e}")
        
        return {"count": processed_count}