"""
수집한 링크들의 텍스트 내용을 추출하는 모듈 (Playwright 사용)
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import json
from pathlib import Path
from urllib.parse import urlparse


class ContentExtractor:
    def __init__(self, delay=1.0, timeout=30000, headless=True, browser_type='chromium'):
        """
        Args:
            delay: 요청 간 대기 시간 (초)
            timeout: 페이지 로드 타임아웃 (밀리초)
            headless: 헤드리스 모드 사용 여부
            browser_type: 브라우저 타입 ('chromium', 'firefox', 'webkit')
        """
        self.delay = delay
        self.timeout = timeout
        self.headless = headless
        self.browser_type = browser_type
        self.playwright = None
        self.browser = None
        self.context = None
    
    def _init_browser(self):
        """브라우저 초기화 (이미 초기화되어 있으면 스킵)"""
        if self.playwright is not None and self.browser is not None and self.context is not None:
            return  # 이미 초기화됨
        
        if self.playwright is None:
            self.playwright = sync_playwright().start()
            
            if self.browser_type == 'chromium':
                self.browser = self.playwright.chromium.launch(headless=self.headless)
            elif self.browser_type == 'firefox':
                self.browser = self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == 'webkit':
                self.browser = self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(f"지원하지 않는 브라우저 타입: {self.browser_type}")
            
            # 컨텍스트 생성
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='ko-KR'
            )
    
    def _close_browser(self):
        """브라우저 종료"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def extract_text_from_url(self, url):
        """
        URL에서 텍스트 내용 추출
        
        Args:
            url: 추출할 URL
            
        Returns:
            추출된 텍스트 (실패 시 None)
        """
        page = None
        try:
            # 브라우저가 초기화되어 있지 않으면 초기화
            if self.context is None:
                self._init_browser()
            
            page = self.context.new_page()
            
            # 페이지 로드
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            except PlaywrightTimeoutError:
                # domcontentloaded가 실패하면 load 시도
                try:
                    page.goto(url, wait_until='load', timeout=self.timeout)
                except:
                    pass
            
            # 추가 대기 (JavaScript 실행 완료 대기)
            page.wait_for_timeout(2000)
            
            # 스크립트와 스타일 태그 제거를 위한 JavaScript 실행
            page.evaluate("""
                // 스크립트와 스타일 태그 제거
                const scripts = document.querySelectorAll('script, style, noscript, iframe');
                scripts.forEach(el => el.remove());
            """)
            
            # body에서 직접 텍스트 추출 (가장 안정적)
            try:
                body = page.query_selector('body')
                if body:
                    text = body.inner_text()
                    if text and len(text.strip()) > 50:  # 최소 50자 이상
                        # 공백 정리
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                        return text
            except Exception as e:
                print(f"  body 텍스트 추출 실패: {e}")
            
            # body가 실패하면 메인 콘텐츠 영역 찾기
            content_selectors = [
                'main',
                'article',
                '[role="main"]',
                '.content',
                '#content',
                '.main-content',
                '.post-content',
                '.entry-content'
            ]
            
            for selector in content_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        text = element.inner_text()
                        if text and len(text.strip()) > 50:
                            # 공백 정리
                            lines = (line.strip() for line in text.splitlines())
                            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                            text = '\n'.join(chunk for chunk in chunks if chunk)
                            return text
                except Exception as e:
                    continue
            
            # 모든 방법 실패 시 페이지 전체 텍스트 추출
            try:
                text = page.inner_text('body')
                if text and len(text.strip()) > 50:
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = '\n'.join(chunk for chunk in chunks if chunk)
                    return text
            except Exception as e:
                print(f"  페이지 전체 텍스트 추출 실패: {e}")
            
            return None
            
        except PlaywrightTimeoutError:
            print(f"  페이지 로드 타임아웃: {url}")
            return None
        except Exception as e:
            print(f"  텍스트 추출 실패: {url} - {e}")
            return None
        finally:
            if page:
                try:
                    page.close()
                except:
                    pass
    
    def extract_from_links(self, links, output_file=None):
        """
        여러 링크에서 텍스트 내용 추출
        
        Args:
            links: URL 리스트
            output_file: 결과를 저장할 파일 경로 (선택사항)
            
        Returns:
            URL과 텍스트를 매핑한 딕셔너리
        """
        results = {}
        total = len(links)
        
        print(f"\n총 {total}개 링크에서 텍스트 추출 시작...\n")
        
        # 브라우저 초기화 (한 번만)
        self._init_browser()
        
        try:
            for i, url in enumerate(links, 1):
                print(f"[{i}/{total}] 처리 중: {url[:80]}...")
                
                text = self.extract_text_from_url(url)
                
                if text:
                    results[url] = text
                    print(f"  성공: {len(text)}자 추출")
                else:
                    print(f"  실패: 텍스트 추출 불가")
                    results[url] = None
                
                # 요청 간 대기
                if i < total:
                    time.sleep(self.delay)
        
        finally:
            # 브라우저 종료
            self._close_browser()
        
        # 결과 저장
        if output_file:
            self.save_results(results, output_file)
        
        success_count = sum(1 for v in results.values() if v is not None)
        print(f"\n완료: {success_count}/{total}개 링크에서 텍스트 추출 성공")
        
        return results
    
    def save_results(self, results, filepath):
        """
        추출 결과를 파일에 저장
        
        Args:
            results: URL과 텍스트를 매핑한 딕셔너리
            filepath: 저장할 파일 경로
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n결과를 {filepath}에 저장했습니다.")
    
    def load_results(self, filepath):
        """
        저장된 결과 로드
        
        Args:
            filepath: 로드할 파일 경로
            
        Returns:
            URL과 텍스트를 매핑한 딕셔너리
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        print(f"{len(results)}개 결과를 {filepath}에서 로드했습니다.")
        return results
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self._init_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self._close_browser()


if __name__ == "__main__":
    # 테스트
    extractor = ContentExtractor(delay=1.0, headless=True)
    
    # 테스트 링크
    test_links = [
        "https://www.python.org",
        "https://www.wikipedia.org",
    ]
    
    results = extractor.extract_from_links(test_links, output_file="data/crawling/data/extracted_content.json")
    
    # 결과 확인
    for url, text in list(results.items())[:2]:
        if text:
            print(f"\n{url}:")
            print(text[:200] + "..." if len(text) > 200 else text)
