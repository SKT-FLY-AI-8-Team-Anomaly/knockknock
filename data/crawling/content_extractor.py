"""
수집한 링크들의 텍스트 내용을 추출하는 모듈 (Playwright 사용)
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import json
from pathlib import Path
from urllib.parse import urlparse

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    print("경고: trafilatura가 설치되지 않았습니다. 본문 추출 품질이 떨어질 수 있습니다.")
    print("설치: pip install trafilatura")


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
        URL에서 본문 텍스트 내용 추출 (광고, 사이드바 등 제외)
        
        Args:
            url: 추출할 URL
            
        Returns:
            추출된 본문 텍스트 (실패 시 None)
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
            
            # trafilatura를 사용한 본문 추출 (가장 우선)
            if TRAFILATURA_AVAILABLE:
                try:
                    # HTML 가져오기
                    html_content = page.content()
                    
                    # trafilatura로 본문 추출 (output_format='txt' 또는 생략)
                    extracted = trafilatura.extract(
                        html_content,
                        url=url,
                        include_comments=False,
                        include_tables=True,
                        include_images=False,
                        include_links=False,
                        output_format='txt'  # 'plaintext'가 아니라 'txt' 사용
                    )
                    
                    if extracted and len(extracted.strip()) > 50:
                        # 공백 정리
                        lines = (line.strip() for line in extracted.splitlines())
                        text = '\n'.join(line for line in lines if line)
                        if text and len(text.strip()) > 50:
                            return text
                except Exception as e:
                    print(f"  trafilatura 추출 실패, 대체 방법 시도: {e}")
            
            # trafilatura 실패 시 JavaScript로 본문 추출 시도
            text = self._extract_main_content_with_js(page)
            if text:
                return text
            
            # JavaScript 방법도 실패하면 기존 방법들 시도
            text = self._extract_with_selectors(page)
            if text:
                return text
            
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
    
    def _extract_main_content_with_js(self, page):
        """
        JavaScript를 사용하여 본문 추출 (광고, 사이드바 등 제거)
        """
        try:
            # 불필요한 요소 제거 및 본문 추출
            text = page.evaluate("""
                () => {
                    // 불필요한 요소 제거
                    const unwantedSelectors = [
                        'nav', 'header', 'footer', 'aside', 'sidebar',
                        '.ad', '.advertisement', '.ads', '.ad-banner',
                        '.sidebar', '.side-menu', '.navigation',
                        '.menu', '.nav', '.header', '.footer',
                        '.comment', '.comments', '.comment-section',
                        '.related', '.related-posts', '.recommend',
                        '.social', '.share', '.sns',
                        'script', 'style', 'noscript', 'iframe',
                        '[role="navigation"]', '[role="banner"]', '[role="complementary"]',
                        '[class*="ad"]', '[class*="advertisement"]', '[id*="ad"]',
                        '[class*="sidebar"]', '[class*="menu"]', '[class*="nav"]'
                    ];
                    
                    unwantedSelectors.forEach(selector => {
                        try {
                            document.querySelectorAll(selector).forEach(el => el.remove());
                        } catch(e) {}
                    });
                    
                    // 본문 영역 찾기 (우선순위 순)
                    const contentSelectors = [
                        'article',
                        'main',
                        '[role="main"]',
                        '.post-content',
                        '.entry-content',
                        '.article-content',
                        '.content-body',
                        '.article-body',
                        '.post-body',
                        '.entry-body',
                        '#content',
                        '.content',
                        '.main-content',
                        '.article',
                        '.post'
                    ];
                    
                    for (const selector of contentSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            const text = element.innerText || element.textContent;
                            if (text && text.trim().length > 100) {
                                return text.trim();
                            }
                        }
                    }
                    
                    // 본문 영역을 찾지 못한 경우, 가장 긴 텍스트 블록 찾기
                    const paragraphs = Array.from(document.querySelectorAll('p'));
                    if (paragraphs.length > 0) {
                        const mainContent = paragraphs
                            .map(p => p.innerText || p.textContent)
                            .filter(text => text.trim().length > 20)
                            .join('\\n\\n');
                        
                        if (mainContent.trim().length > 100) {
                            return mainContent.trim();
                        }
                    }
                    
                    return null;
                }
            """)
            
            if text and len(text.strip()) > 50:
                # 공백 정리
                lines = (line.strip() for line in text.splitlines())
                cleaned_text = '\n'.join(line for line in lines if line)
                if cleaned_text and len(cleaned_text.strip()) > 50:
                    return cleaned_text
            
            return None
        except Exception as e:
            return None
    
    def _extract_with_selectors(self, page):
        """
        기존 선택자 기반 추출 방법 (fallback)
        """
        # 메인 콘텐츠 영역 찾기
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.content-body',
            '.article-body',
            '.post-body',
            '.entry-body',
            '#content',
            '.content',
            '.main-content'
        ]
        
        for selector in content_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text()
                    if text and len(text.strip()) > 50:
                        # 공백 정리
                        lines = (line.strip() for line in text.splitlines())
                        cleaned_text = '\n'.join(line for line in lines if line)
                        if cleaned_text and len(cleaned_text.strip()) > 50:
                            return cleaned_text
            except Exception:
                continue
        
        return None
    
    def extract_from_links(self, links, output_file=None, save_interval=10):
        """
        여러 링크에서 텍스트 내용 추출
        
        Args:
            links: URL 리스트
            output_file: 결과를 저장할 파일 경로 (선택사항)
            save_interval: 중간 저장 간격 (N개 링크마다 저장, 0이면 중간 저장 안함)
            
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
                
                # 중간 저장 (설정된 간격마다)
                if output_file and save_interval > 0 and i % save_interval == 0:
                    # 기존 결과 로드 (있는 경우)
                    existing_results = {}
                    if Path(output_file).exists():
                        try:
                            with open(output_file, 'r', encoding='utf-8') as f:
                                existing_results = json.load(f)
                        except:
                            pass
                    
                    # 병합 후 저장
                    all_results = {**existing_results, **results}
                    self.save_results(all_results, output_file)
                    print(f"  [중간 저장] {i}개 링크 처리 완료, 결과 저장됨")
                
                # 요청 간 대기
                if i < total:
                    time.sleep(self.delay)
        
        except KeyboardInterrupt:
            print("\n\n사용자에 의해 중단되었습니다.")
            # 중단 시에도 결과 저장
            if output_file:
                existing_results = {}
                if Path(output_file).exists():
                    try:
                        with open(output_file, 'r', encoding='utf-8') as f:
                            existing_results = json.load(f)
                    except:
                        pass
                all_results = {**existing_results, **results}
                self.save_results(all_results, output_file)
                print(f"중단된 시점까지의 결과를 {output_file}에 저장했습니다.")
            raise
        
        finally:
            # 브라우저 종료
            self._close_browser()
        
        # 최종 결과 저장
        if output_file:
            # 기존 결과와 병합
            existing_results = {}
            if Path(output_file).exists():
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_results = json.load(f)
                except:
                    pass
            all_results = {**existing_results, **results}
            self.save_results(all_results, output_file)
        
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
