from typing import Dict, Any, List
import PyPDF2
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """문서 전처리 및 정제 클래스"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.txt', '.md']
    
    async def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """문서 전처리 메인 함수"""
        try:
            processed_doc = document.copy()
            
            # 텍스트 정제
            if 'content' in processed_doc:
                processed_doc['content'] = self._clean_text(processed_doc['content'])
            
            if 'abstract' in processed_doc:
                processed_doc['abstract'] = self._clean_text(processed_doc['abstract'])
            
            # 메타데이터 정제
            processed_doc = self._clean_metadata(processed_doc)
            
            # 키워드 추출
            processed_doc['extracted_keywords'] = self._extract_keywords(
                processed_doc.get('content', '') + ' ' + processed_doc.get('abstract', '')
            )
            
            # 언어 감지
            processed_doc['language'] = self._detect_language(processed_doc.get('content', ''))
            
            return processed_doc
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise
    
    async def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """PDF 파일 처리"""
        try:
            document = {
                'content': '',
                'title': Path(pdf_path).stem,
                'source': 'pdf_upload',
                'file_path': pdf_path
            }
            
            # PDF 텍스트 추출
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                content = ''
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    content += page.extract_text() + '\n'
                
                document['content'] = content
            
            # 메타데이터 추출 시도
            metadata = self._extract_pdf_metadata(pdf_path)
            document.update(metadata)
            
            return await self.process_document(document)
            
        except Exception as e:
            logger.error(f"PDF processing failed for {pdf_path}: {e}")
            raise
    
    async def process_text_file(self, file_path: str) -> Dict[str, Any]:
        """텍스트 파일 처리"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            document = {
                'content': content,
                'title': Path(file_path).stem,
                'source': 'text_upload',
                'file_path': file_path
            }
            
            return await self.process_document(document)
            
        except Exception as e:
            logger.error(f"Text file processing failed for {file_path}: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""
        
        # 과도한 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 특수문자 정리 (한글, 영문, 숫자, 기본 문장부호만 유지)
        text = re.sub(r'[^\w\s가-힣.,!?;:()\-\'\"]+', ' ', text)
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    def _clean_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터 정제"""
        cleaned = document.copy()
        
        # 제목 정제
        if 'title' in cleaned:
            cleaned['title'] = self._clean_text(cleaned['title'])[:200]  # 최대 200자
        
        # 저자 정보 정제
        if 'authors' in cleaned:
            if isinstance(cleaned['authors'], str):
                # 문자열을 리스트로 변환
                authors = [author.strip() for author in cleaned['authors'].split(',')]
                cleaned['authors'] = [self._clean_text(author) for author in authors if author.strip()]
            elif isinstance(cleaned['authors'], list):
                cleaned['authors'] = [self._clean_text(str(author)) for author in cleaned['authors']]
        
        # 연도 정제
        if 'year' in cleaned:
            try:
                year = int(cleaned['year'])
                if 1900 <= year <= 2030:  # 합리적인 연도 범위
                    cleaned['year'] = year
                else:
                    cleaned['year'] = 0
            except (ValueError, TypeError):
                cleaned['year'] = 0
        
        # 소스 정보 정제
        if 'source' in cleaned:
            cleaned['source'] = self._clean_text(cleaned['source'])[:100]
        
        return cleaned
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """키워드 추출 (간단한 빈도 기반)"""
        if not text:
            return []
        
        # 불용어 목록
        stopwords = {
            '이', '그', '저', '것', '들', '에', '를', '은', '는', '이다', '하다', '되다',
            '있다', '없다', '같다', '다른', '많다', '크다', '작다', '좋다', '나쁘다',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had'
        }
        
        # 단어 추출 (2글자 이상)
        words = re.findall(r'\b[가-힣a-zA-Z]{2,}\b', text.lower())
        
        # 불용어 제거 및 빈도 계산
        word_freq = {}
        for word in words:
            if word not in stopwords:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 빈도순 정렬하여 상위 키워드 반환
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
    
    def _detect_language(self, text: str) -> str:
        """언어 감지 (간단한 휴리스틱)"""
        if not text:
            return "unknown"
        
        # 한글 문자 비율 계산
        korean_chars = len(re.findall(r'[가-힣]', text))
        total_chars = len(re.findall(r'[가-힣a-zA-Z]', text))
        
        if total_chars == 0:
            return "unknown"
        
        korean_ratio = korean_chars / total_chars
        
        if korean_ratio > 0.5:
            return "korean"
        elif korean_ratio < 0.1:
            return "english"
        else:
            return "mixed"
    
    def _extract_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """PDF 메타데이터 추출"""
        metadata = {}
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if pdf_reader.metadata:
                    pdf_meta = pdf_reader.metadata
                    
                    # PDF 메타데이터에서 정보 추출
                    if '/Title' in pdf_meta:
                        metadata['title'] = str(pdf_meta['/Title'])
                    
                    if '/Author' in pdf_meta:
                        metadata['authors'] = [str(pdf_meta['/Author'])]
                    
                    if '/CreationDate' in pdf_meta:
                        # 날짜에서 연도 추출 시도
                        try:
                            date_str = str(pdf_meta['/CreationDate'])
                            year_match = re.search(r'(\d{4})', date_str)
                            if year_match:
                                metadata['year'] = int(year_match.group(1))
                        except:
                            pass
                
                # 페이지 수 추가
                metadata['page_count'] = len(pdf_reader.pages)
                
        except Exception as e:
            logger.warning(f"Failed to extract PDF metadata from {pdf_path}: {e}")
        
        return metadata
    
    def _extract_abstract(self, content: str) -> str:
        """본문에서 초록 추출 시도"""
        if not content:
            return ""
        
        # 초록 섹션 찾기
        abstract_patterns = [
            r'abstract[:\s]+(.*?)(?=\n\s*\n|\n\s*keywords|\n\s*introduction)',
            r'요약[:\s]+(.*?)(?=\n\s*\n|\n\s*키워드|\n\s*서론)',
            r'초록[:\s]+(.*?)(?=\n\s*\n|\n\s*주제어|\n\s*1\.|I\.)'
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                if len(abstract) > 50:  # 최소 길이 체크
                    return abstract[:500]  # 최대 500자
        
        # 초록을 찾지 못했으면 첫 번째 단락 반환
        paragraphs = content.split('\n\n')
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if len(paragraph) > 100:  # 의미있는 길이의 단락
                return paragraph[:500]
        
        return ""
    
    async def batch_process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """문서 배치 처리"""
        processed_documents = []
        
        for doc in documents:
            try:
                processed_doc = await self.process_document(doc)
                processed_documents.append(processed_doc)
            except Exception as e:
                logger.error(f"Failed to process document {doc.get('title', 'unknown')}: {e}")
                # 처리 실패한 문서도 기본 정보만으로 추가
                processed_documents.append({
                    'title': doc.get('title', 'Unknown'),
                    'content': doc.get('content', ''),
                    'processing_error': str(e)
                })
        
        return processed_documents