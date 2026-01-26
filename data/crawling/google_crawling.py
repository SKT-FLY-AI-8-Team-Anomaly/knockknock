"""
구글 검색 결과에서 링크를 수집하는 모듈 (Playwright 사용)
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
from urllib.parse import urlparse, parse_qs


class GoogleCrawler:
    def __init__(self, delay=1.0, headless=True, browser_type='chromium'):
        """
        Args:
            delay: 요청 간 대기 시간 (초)
            headless: 헤드리스 모드 사용 여부
            browser_type: 브라우저 타입 ('chromium', 'firefox', 'webkit')
        """
        self.delay = delay
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
            
            # 브라우저 실행 옵션 (봇 감지 우회)
            launch_options = {
                'headless': self.headless,
                'args': [
                    '--disable-blink-features=AutomationControlled',  # 자동화 감지 비활성화
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            }
            
            if self.browser_type == 'chromium':
                self.browser = self.playwright.chromium.launch(**launch_options)
            elif self.browser_type == 'firefox':
                self.browser = self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == 'webkit':
                self.browser = self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(f"지원하지 않는 브라우저 타입: {self.browser_type}")
            
            # 컨텍스트 생성 (User-Agent 등 설정 - 봇 감지 우회)
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='ko-KR',
                # 봇 감지 우회를 위한 추가 설정
                java_script_enabled=True,
                bypass_csp=True,
                # 실제 브라우저처럼 보이도록
                permissions=['geolocation'],
                geolocation={'latitude': 37.5665, 'longitude': 126.9780},  # 서울
                timezone_id='Asia/Seoul',
                # 언어 설정
                extra_http_headers={
                    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # 자동화 감지 스크립트 제거
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Chrome 객체 추가
                window.chrome = {
                    runtime: {}
                };
                
                // Permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
    
    def _close_browser(self):
        """브라우저 종료"""
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
    
    def extract_links_from_page(self, page):
        """
        페이지에서 검색 결과 링크를 추출 (블로그, 뉴스, 카페 등)
        
        Args:
            page: Playwright Page 객체
            
        Returns:
            링크 URL 리스트
        """
        links = []
        seen_urls = set()
        
        try:
            # 페이지 제목 확인 (디버깅)
            try:
                page_title = page.title()
                print(f"  페이지 제목: {page_title[:50]}...")
            except:
                pass
            
            # JavaScript로 동적 링크도 가져오기
            # 구글 검색 결과의 실제 링크를 JavaScript로 추출
            js_links = page.evaluate("""
                () => {
                    const links = [];
                    const seen = new Set();
                    
                    // 방법 1: 모든 a 태그에서 찾기
                    const allLinks = document.querySelectorAll('a[href]');
                    allLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href && !seen.has(href)) {
                            seen.add(href);
                            links.push(href);
                        }
                    });
                    
                    // 방법 2: 검색 결과 컨테이너에서 찾기
                    const selectors = [
                        'div.g',
                        'div[data-ved]',
                        'div.tF2Cxc',
                        'div[class*="g"]',
                        'div[data-sokoban-container]',
                        'h3',
                        'div.yuRUbf'
                    ];
                    
                    selectors.forEach(selector => {
                        const containers = document.querySelectorAll(selector);
                        containers.forEach(container => {
                            const linkElement = container.querySelector('a[href]');
                            if (linkElement) {
                                const href = linkElement.getAttribute('href');
                                if (href && !seen.has(href)) {
                                    seen.add(href);
                                    links.push(href);
                                }
                            }
                        });
                    });
                    
                    // 방법 3: data-ved 속성이 있는 링크 찾기 (구글 검색 결과 특징)
                    const vedLinks = document.querySelectorAll('a[data-ved][href]');
                    vedLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href && !seen.has(href)) {
                            seen.add(href);
                            links.push(href);
                        }
                    });
                    
                    return links;
                }
            """)
            
            print(f"  JavaScript로 {len(js_links)}개 링크 후보 발견")
            
            # 디버깅: 처음 몇 개 링크 출력
            if len(js_links) > 0:
                print(f"  샘플 링크 (처음 3개): {js_links[:3]}")
            else:
                # 링크가 없을 때 페이지 구조 확인
                try:
                    debug_info = page.evaluate("""
                        () => {
                            return {
                                totalLinks: document.querySelectorAll('a[href]').length,
                                containers: document.querySelectorAll('div.g, div[data-ved], div.tF2Cxc').length,
                                urlLinks: document.querySelectorAll('a[href*="/url?q="]').length,
                                httpLinks: document.querySelectorAll('a[href^="http"]').length,
                                bodyText: document.body.innerText.substring(0, 200)
                            };
                        }
                    """)
                    print(f"  디버깅 정보:")
                    print(f"    - 총 a 태그: {debug_info.get('totalLinks', 0)}개")
                    print(f"    - 검색 결과 컨테이너: {debug_info.get('containers', 0)}개")
                    print(f"    - /url?q= 링크: {debug_info.get('urlLinks', 0)}개")
                    print(f"    - http 링크: {debug_info.get('httpLinks', 0)}개")
                    print(f"    - 페이지 텍스트 샘플: {debug_info.get('bodyText', '')[:100]}...")
                except Exception as e:
                    print(f"  디버깅 정보 수집 실패: {e}")
            
            # JavaScript로 추출한 링크 처리
            for href in js_links:
                try:
                    if href and isinstance(href, str):
                        if href.startswith('/url?q='):
                            # /url?q= 뒤의 실제 URL 추출
                            try:
                                parsed = parse_qs(urlparse(href).query)
                                if 'q' in parsed:
                                    url = parsed['q'][0]
                                    # 구글 내부 링크 제외, http/https로 시작하는 링크만
                                    if (url.startswith('http://') or url.startswith('https://')) and 'google.com' not in url:
                                        if url not in seen_urls:
                                            links.append(url)
                                            seen_urls.add(url)
                            except Exception:
                                continue
                        elif href.startswith('http://') or href.startswith('https://'):
                            # 직접 링크인 경우
                            if 'google.com' not in href and href not in seen_urls:
                                links.append(href)
                                seen_urls.add(href)
                except Exception as e:
                    continue
            
            print(f"  처리 후 {len(links)}개 유효한 링크 추출됨")
            
            # 추가 방법: Playwright 선택자로도 시도
            # 검색 결과 링크 선택자들
            selectors = [
                'a[href*="/url?q="]',
                'div.g a[href^="http"]:not([href*="google.com"])',
                'div[data-ved] a[href^="http"]:not([href*="google.com"])',
                'h3 a[href^="http"]:not([href*="google.com"])'
            ]
            
            for selector in selectors:
                try:
                    result_links = page.query_selector_all(selector)
                    for link_element in result_links:
                        try:
                            href = link_element.get_attribute('href')
                            if href:
                                if href.startswith('/url?q='):
                                    parsed = parse_qs(urlparse(href).query)
                                    if 'q' in parsed:
                                        url = parsed['q'][0]
                                        if (url.startswith('http://') or url.startswith('https://')) and 'google.com' not in url:
                                            if url not in seen_urls:
                                                links.append(url)
                                                seen_urls.add(url)
                                elif (href.startswith('http://') or href.startswith('https://')) and 'google.com' not in href:
                                    if href not in seen_urls:
                                        links.append(href)
                                        seen_urls.add(href)
                        except Exception:
                            continue
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"  링크 추출 중 오류: {e}")
            import traceback
            traceback.print_exc()
        
        return links
    
    def get_search_results_page(self, search_url, page_num=0):
        """
        구글 검색 결과 페이지 가져오기
        
        Args:
            search_url: 구글 검색 URL
            page_num: 페이지 번호 (0부터 시작)
            
        Returns:
            Playwright Page 객체 (실패 시 None)
        """
        try:
            self._init_browser()
            page = self.context.new_page()
            
            # 페이지 번호에 따라 start 파라미터 추가
            if page_num > 0:
                parsed_url = urlparse(search_url)
                query_params = parse_qs(parsed_url.query)
                query_params['start'] = [str(page_num * 10)]  # 구글은 페이지당 10개 결과
                
                # URL 재구성
                new_query = '&'.join([f"{k}={v[0]}" for k, v in query_params.items()])
                search_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
            
            # 페이지 로드
            try:
                response = page.goto(search_url, wait_until='networkidle', timeout=30000)
                if response:
                    print(f"  페이지 로드 상태: {response.status}")
            except Exception as e:
                print(f"  networkidle 실패, 다른 방법 시도: {e}")
                try:
                    page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                except:
                    page.goto(search_url, wait_until='load', timeout=30000)
            
            # 추가 대기 (JavaScript 실행 완료 대기)
            page.wait_for_timeout(3000)
            
            # 캡차 확인
            try:
                page_content = page.content().lower()
                if 'captcha' in page_content or 'unusual traffic' in page_content or 'our systems have detected' in page_content:
                    print(f"  ⚠️ 캡차 감지됨!")
                    print(f"  해결 방법:")
                    print(f"    1. 헤드리스 모드를 끄고(headless=False) 수동으로 캡차 해결")
                    print(f"    2. 대기 시간을 늘리거나 요청 간격을 늘림")
                    print(f"    3. VPN 사용 또는 IP 변경")
                    # 스크린샷 저장
                    try:
                        page.screenshot(path=f"data/crawling/data/debug_captcha_{page_num}.png", full_page=True)
                        print(f"  스크린샷 저장: data/crawling/data/debug_captcha_{page_num}.png")
                    except:
                        pass
                    return None  # 캡차 페이지는 None 반환
            except:
                pass
            
            # 자연스러운 마우스 움직임 시뮬레이션 (봇 감지 우회)
            import random
            try:
                # 마우스를 약간 움직임
                for _ in range(2):
                    x = random.randint(100, 500)
                    y = random.randint(100, 500)
                    page.mouse.move(x, y)
                    page.wait_for_timeout(random.uniform(300, 800))
            except:
                pass
            
            # 여러 번 스크롤 (동적 콘텐츠 로드 + 자연스러운 동작)
            for i in range(3):
                # 랜덤한 스크롤 위치
                scroll_pos = random.randint(300, 800)
                page.evaluate(f"window.scrollTo({{top: {scroll_pos}, behavior: 'smooth'}})")
                page.wait_for_timeout(random.uniform(1000, 2000))  # 랜덤 대기
            
            # 마지막으로 아래로 스크롤
            page.evaluate("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})")
            page.wait_for_timeout(2000)
            
            # 다시 위로 스크롤 (자연스러운 동작)
            page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            page.wait_for_timeout(1000)
            
            # 페이지가 제대로 로드되었는지 확인
            try:
                page_content = page.content()
                page_url = page.url
                
                # 캡차 확인
                if 'captcha' in page_content.lower() or 'unusual traffic' in page_content.lower():
                    print(f"  경고: 구글이 봇을 감지했습니다. 캡차 페이지일 수 있습니다.")
                    # 스크린샷 저장 (디버깅)
                    try:
                        page.screenshot(path=f"data/crawling/data/debug_captcha_{page_num}.png")
                        print(f"  스크린샷 저장: data/crawling/data/debug_captcha_{page_num}.png")
                    except:
                        pass
                
                # 콘텐츠 크기 확인
                if len(page_content) < 10000:
                    print(f"  경고: 페이지 콘텐츠가 너무 적습니다 ({len(page_content)}자)")
                    print(f"  현재 URL: {page_url[:100]}...")
                    
                    # HTML 일부 출력 (디버깅)
                    try:
                        body_text = page.evaluate("document.body.innerText")
                        print(f"  페이지 텍스트 샘플: {body_text[:200]}...")
                    except:
                        pass
            except Exception as e:
                print(f"  페이지 확인 중 오류: {e}")
            
            return page
            
        except PlaywrightTimeoutError:
            print(f"  페이지 {page_num} 로드 타임아웃")
            return None
        except Exception as e:
            print(f"  페이지 {page_num} 가져오기 실패: {e}")
            return None
    
    def crawl_search_results(self, search_url, max_pages=10, keep_browser_open=False):
        """
        구글 검색 결과를 여러 페이지에 걸쳐 크롤링
        
        Args:
            search_url: 구글 검색 URL
            max_pages: 최대 크롤링할 페이지 수
            keep_browser_open: 브라우저를 열어둘지 여부 (여러 검색 URL 처리 시 True)
            
        Returns:
            수집된 링크 리스트
        """
        all_links = []
        
        print(f"검색 시작: {search_url}")
        
        try:
            for page_num in range(max_pages):
                print(f"페이지 {page_num + 1}/{max_pages} 크롤링 중...")
                
                page = self.get_search_results_page(search_url, page_num)
                
                if page is None:
                    print(f"페이지 {page_num + 1} 가져오기 실패, 중단")
                    break
                
                links = self.extract_links_from_page(page)
                page.close()
                
                if not links:
                    print(f"페이지 {page_num + 1}에서 링크를 찾을 수 없음, 중단")
                    # 디버깅: 페이지 스크린샷 저장 (선택적)
                    # page.screenshot(path=f"debug_page_{page_num}.png")
                    break
                
                all_links.extend(links)
                print(f"페이지 {page_num + 1}에서 {len(links)}개 링크 발견 (총 {len(all_links)}개)")
                
                # 요청 간 대기
                if page_num < max_pages - 1:
                    time.sleep(self.delay)
        
        finally:
            # keep_browser_open이 False일 때만 브라우저 종료
            if not keep_browser_open:
                self._close_browser()
        
        return list(set(all_links))  # 중복 제거
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self._init_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self._close_browser()


if __name__ == "__main__":
    # 테스트
    crawler = GoogleCrawler(delay=1.0, headless=True)
    test_url = "https://www.google.com/search?q=python"
    links = crawler.crawl_search_results(test_url, max_pages=3)
    print(f"\n총 {len(links)}개 링크 수집:")
    for i, link in enumerate(links[:10], 1):
        print(f"{i}. {link}")
