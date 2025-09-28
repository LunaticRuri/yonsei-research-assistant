from typing import Dict, Any, List
from shared.models import SearchStrategy, LibrarySearchResponse, DocumentResult
from .library_scraper import LibraryScraper
import logging

logger = logging.getLogger(__name__)

class SearchExecutor:
    """검색 전략을 실제 도서관 검색으로 실행하는 클래스"""
    
    def __init__(self, library_scraper: LibraryScraper):
        self.scraper = library_scraper
        self.search_cache = {}  # 검색 결과 캐싱
    
    async def execute_search(
        self,
        search_strategy: SearchStrategy,
        session_id: str,
        max_results: int = 20
    ) -> LibrarySearchResponse:
        """검색 전략을 실제 도서관 검색으로 실행"""
        
        try:
            # 검색 쿼리 구성
            search_query = self._build_search_query(search_strategy)
            
            logger.info(f"Executing search for session {session_id}: {search_query}")
            
            # 도서관 검색 실행
            raw_results = await self.scraper.execute_library_search(
                query=search_query,
                search_type="integrated",
                max_results=max_results
            )
            
            # 결과 후처리
            processed_results = await self._process_search_results(raw_results)
            
            # 결과 랭킹 및 필터링
            ranked_results = self._rank_and_filter_results(
                processed_results, search_strategy
            )
            
            # 연세대 도서관 이용 정보 추가
            final_results = await self._add_access_information(ranked_results)
            
            # 검색 요약 생성
            search_summary = self._generate_search_summary(
                search_strategy, len(final_results), len(raw_results)
            )
            
            return LibrarySearchResponse(
                session_id=session_id,
                search_query_used=search_query,
                total_found=len(raw_results),
                results=final_results,
                search_summary=search_summary,
                recommendations=self._generate_search_recommendations(
                    search_strategy, final_results
                )
            )
            
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            raise
    
    def _build_search_query(self, strategy: SearchStrategy) -> str:
        """검색 전략을 실제 검색 쿼리로 변환"""
        
        # 불리언 쿼리가 있으면 우선 사용
        if strategy.boolean_query:
            return strategy.boolean_query
        
        # 그렇지 않으면 키워드들로 쿼리 구성
        query_parts = []
        
        # 주요 키워드 (OR 연결)
        if strategy.primary_keywords:
            primary_part = " OR ".join([f'"{kw}"' for kw in strategy.primary_keywords])
            query_parts.append(f"({primary_part})")
        
        # 확장 키워드 (AND로 추가)
        if strategy.expansion_keywords:
            expansion_part = " OR ".join([f'"{kw}"' for kw in strategy.expansion_keywords[:3]])
            query_parts.append(f"({expansion_part})")
        
        # 최종 쿼리 조합
        if len(query_parts) > 1:
            return " AND ".join(query_parts)
        elif len(query_parts) == 1:
            return query_parts[0]
        else:
            # 키워드가 없으면 기본 검색
            return " ".join(strategy.primary_keywords) if strategy.primary_keywords else ""
    
    async def _process_search_results(
        self, 
        raw_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """검색 결과 후처리"""
        
        processed_results = []
        
        for result in raw_results:
            try:
                # 결과 정제
                processed_result = self._clean_search_result(result)
                
                # 관련성 점수 계산
                processed_result['relevance_score'] = self._calculate_relevance_score(result)
                
                # 중복 제거 체크
                if not self._is_duplicate_result(processed_result, processed_results):
                    processed_results.append(processed_result)
                    
            except Exception as e:
                logger.warning(f"Failed to process result: {e}")
                continue
        
        return processed_results
    
    def _rank_and_filter_results(
        self, 
        results: List[Dict[str, Any]], 
        strategy: SearchStrategy
    ) -> List[Dict[str, Any]]:
        """결과 랭킹 및 필터링"""
        
        # 관련성 점수로 정렬
        ranked_results = sorted(
            results, 
            key=lambda x: x.get('relevance_score', 0), 
            reverse=True
        )
        
        # 필터링 기준 적용
        filtered_results = []
        
        for result in ranked_results:
            # 기본 품질 체크
            if self._meets_quality_criteria(result):
                # 전략과의 일치도 체크
                if self._matches_strategy(result, strategy):
                    filtered_results.append(result)
        
        return filtered_results
    
    async def _add_access_information(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[DocumentResult]:
        """연세대 도서관 이용 정보 추가"""
        
        final_results = []
        
        for result in results:
            try:
                # 소장 여부 확인
                holdings_info = await self.scraper.check_holdings(
                    title=result.get('title', ''),
                    authors=result.get('authors', [])
                )
                
                # DocumentResult 객체 생성
                document_result = DocumentResult(
                    title=result.get('title', ''),
                    authors=result.get('authors', []),
                    publication_year=result.get('year', 0),
                    source=result.get('publication_info', ''),
                    abstract=result.get('abstract', ''),
                    relevance_score=result.get('relevance_score', 0.0),
                    yonsei_library_status=holdings_info.get('access_info', ''),
                    access_link=result.get('detail_link', '')
                )
                
                final_results.append(document_result)
                
            except Exception as e:
                logger.warning(f"Failed to add access info for {result.get('title', 'Unknown')}: {e}")
                # 기본 정보만으로 결과 추가
                document_result = DocumentResult(
                    title=result.get('title', 'Unknown Title'),
                    authors=result.get('authors', []),
                    publication_year=result.get('year', 0),
                    source=result.get('publication_info', ''),
                    abstract=result.get('abstract', ''),
                    relevance_score=result.get('relevance_score', 0.0),
                    yonsei_library_status="소장 정보 확인 필요",
                    access_link=result.get('detail_link', '')
                )
                final_results.append(document_result)
        
        return final_results
    
    def _generate_search_summary(
        self, 
        strategy: SearchStrategy, 
        final_count: int, 
        total_count: int
    ) -> str:
        """검색 요약 생성"""
        
        summary = f"""
        검색 전략: {', '.join(strategy.primary_keywords)}
        
        검색 결과:
        - 전체 검색 결과: {total_count}개
        - 필터링된 결과: {final_count}개
        
        사용된 검색식: {strategy.boolean_query or '키워드 기반 검색'}
        
        검색 범위: 연세대학교 학술정보원 통합검색
        """
        
        return summary.strip()
    
    def _generate_search_recommendations(
        self, 
        strategy: SearchStrategy, 
        results: List[DocumentResult]
    ) -> List[str]:
        """검색 개선 권장사항 생성"""
        
        recommendations = []
        
        # 결과 수에 따른 권장사항
        if len(results) < 5:
            recommendations.append("검색 결과가 적습니다. 더 넓은 키워드를 사용해보세요.")
            recommendations.append("동의어나 관련 용어를 추가해보세요.")
        elif len(results) > 50:
            recommendations.append("검색 결과가 많습니다. 더 구체적인 키워드를 사용해보세요.")
            recommendations.append("특정 기간이나 자료 유형으로 필터링해보세요.")
        
        # 검색 전략에 따른 권장사항
        if len(strategy.primary_keywords) < 3:
            recommendations.append("더 다양한 키워드를 추가하여 검색 범위를 확장해보세요.")
        
        # 기본 권장사항
        recommendations.append("관심 있는 자료는 즐겨찾기에 추가하여 나중에 다시 확인하세요.")
        recommendations.append("전문이 필요한 경우 도서관 사서에게 문의하세요.")
        
        return recommendations[:3]  # 최대 3개
    
    def _clean_search_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """검색 결과 정제"""
        
        cleaned = result.copy()
        
        # 제목 정제
        if 'title' in cleaned:
            title = cleaned['title'].strip()
            # HTML 태그 제거
            import re
            title = re.sub(r'<[^>]+>', '', title)
            cleaned['title'] = title
        
        # 저자 정보 정제
        if 'authors' in cleaned and isinstance(cleaned['authors'], list):
            cleaned['authors'] = [author.strip() for author in cleaned['authors'] if author.strip()]
        
        # 초록 정제 (길이 제한)
        if 'abstract' in cleaned and len(cleaned['abstract']) > 300:
            cleaned['abstract'] = cleaned['abstract'][:297] + "..."
        
        return cleaned
    
    def _calculate_relevance_score(self, result: Dict[str, Any]) -> float:
        """관련성 점수 계산"""
        
        score = 0.5  # 기본 점수
        
        # 제목 길이 (너무 짧거나 길면 감점)
        title = result.get('title', '')
        if 10 <= len(title) <= 100:
            score += 0.1
        
        # 저자 정보 존재
        if result.get('authors'):
            score += 0.1
        
        # 초록 존재
        if result.get('abstract'):
            score += 0.1
        
        # 출판 연도 (최근일수록 가점)
        year = result.get('year', 0)
        if year >= 2020:
            score += 0.2
        elif year >= 2010:
            score += 0.1
        
        return min(score, 1.0)
    
    def _is_duplicate_result(
        self, 
        result: Dict[str, Any], 
        existing_results: List[Dict[str, Any]]
    ) -> bool:
        """중복 결과 확인"""
        
        title = result.get('title', '').lower()
        
        for existing in existing_results:
            existing_title = existing.get('title', '').lower()
            
            # 제목 유사도 체크 (간단한 버전)
            if self._calculate_title_similarity(title, existing_title) > 0.8:
                return True
        
        return False
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """제목 유사도 계산 (간단한 버전)"""
        
        if not title1 or not title2:
            return 0.0
        
        # 단어 집합으로 비교
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _meets_quality_criteria(self, result: Dict[str, Any]) -> bool:
        """품질 기준 충족 여부"""
        
        # 필수 정보 체크
        if not result.get('title'):
            return False
        
        # 제목 길이 체크
        title = result.get('title', '')
        if len(title) < 5 or len(title) > 200:
            return False
        
        return True
    
    def _matches_strategy(self, result: Dict[str, Any], strategy: SearchStrategy) -> bool:
        """검색 전략과의 일치 여부"""
        
        # 간단한 키워드 매칭
        title = result.get('title', '').lower()
        abstract = result.get('abstract', '').lower()
        content = title + " " + abstract
        
        # 주요 키워드 중 하나라도 포함되어야 함
        for keyword in strategy.primary_keywords:
            if keyword.lower() in content:
                return True
        
        return False