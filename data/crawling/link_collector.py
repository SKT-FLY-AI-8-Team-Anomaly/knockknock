"""
여러 검색 주소에서 링크를 수집하고 중복을 제거하는 모듈
"""
import json
import sys
from pathlib import Path

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from google_crawling import GoogleCrawler


def load_exclude_patterns_from_file(filepath):
    """
    JSON 파일에서 제외 패턴 리스트를 로드
    
    지원 형식:
    - JSON: ["pattern1", "pattern2", ...] 또는 {"patterns": ["pattern1", ...]}
    
    Args:
        filepath: 제외 패턴 JSON 파일 경로
        
    Returns:
        제외 패턴 리스트
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        print(f"제외 패턴 파일을 찾을 수 없습니다: {filepath} (무시하고 계속합니다)")
        return []
    
    # JSON 파일만 지원
    if filepath.suffix.lower() != '.json':
        raise ValueError(f"JSON 파일만 지원합니다. 파일 확장자가 .json이어야 합니다: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                patterns = [pattern.strip() for pattern in data if pattern.strip()]
            elif isinstance(data, dict) and 'patterns' in data:
                patterns = [pattern.strip() for pattern in data['patterns'] if pattern.strip()]
            else:
                raise ValueError("JSON 파일은 패턴 리스트 또는 {'patterns': [...]} 형식이어야 합니다.")
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파일 형식이 올바르지 않습니다: {e}")
    
    if patterns:
        print(f"{len(patterns)}개 제외 패턴을 {filepath}에서 로드했습니다.")
        print(f"제외 패턴: {', '.join(patterns)}")
    else:
        print(f"제외 패턴 파일이 비어있습니다: {filepath}")
    
    return patterns


def load_search_urls_from_file(filepath):
    """
    JSON 파일에서 검색 URL 리스트를 로드
    
    지원 형식:
    - JSON: ["url1", "url2", ...] 또는 {"urls": ["url1", ...]}
    
    Args:
        filepath: 검색 URL JSON 파일 경로
        
    Returns:
        검색 URL 리스트
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")
    
    # JSON 파일만 지원
    if filepath.suffix.lower() != '.json':
        raise ValueError(f"JSON 파일만 지원합니다. 파일 확장자가 .json이어야 합니다: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                urls = [url.strip() for url in data if url.strip()]
            elif isinstance(data, dict) and 'urls' in data:
                urls = [url.strip() for url in data['urls'] if url.strip()]
            else:
                raise ValueError("JSON 파일은 URL 리스트 또는 {'urls': [...]} 형식이어야 합니다.")
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파일 형식이 올바르지 않습니다: {e}")
    
    if not urls:
        raise ValueError(f"파일에서 유효한 URL을 찾을 수 없습니다: {filepath}")
    
    print(f"{len(urls)}개 검색 URL을 {filepath}에서 로드했습니다.")
    return urls


class LinkCollector:
    def __init__(self, delay=1.0, headless=True, browser_type='chromium', exclude_patterns=None):
        """
        Args:
            delay: 요청 간 대기 시간 (초)
            headless: 헤드리스 모드 사용 여부
            browser_type: 브라우저 타입 ('chromium', 'firefox', 'webkit')
            exclude_patterns: 제외할 URL 패턴 리스트 (문자열 또는 정규식 패턴)
        """
        self.crawler = GoogleCrawler(delay=delay, headless=headless, browser_type=browser_type)
        self.all_links = set()
        self.excluded_links = set()
        self.exclude_patterns = exclude_patterns or []
    
    def should_exclude_link(self, link):
        """
        링크가 제외 패턴과 매칭되는지 확인
        
        Args:
            link: 확인할 URL 문자열
            
        Returns:
            제외해야 하면 True, 아니면 False
        """
        if not self.exclude_patterns:
            return False
        
        for pattern in self.exclude_patterns:
            # 패턴이 링크에 포함되어 있으면 제외
            if pattern in link:
                return True
        
        return False
    
    def collect_from_search_urls(self, search_urls, max_pages_per_search=10):
        """
        여러 검색 주소에서 링크 수집
        
        Args:
            search_urls: 검색 URL 리스트
            max_pages_per_search: 각 검색당 최대 페이지 수
            
        Returns:
            중복 제거된 링크 리스트
        """
        self.all_links = set()
        
        try:
            for i, search_url in enumerate(search_urls, 1):
                print(f"\n[{i}/{len(search_urls)}] 검색 URL 처리 중: {search_url}")
                
                try:
                    # 마지막 검색이 아니면 브라우저를 열어둠
                    keep_open = (i < len(search_urls))
                    links = self.crawler.crawl_search_results(
                        search_url, 
                        max_pages=max_pages_per_search,
                        keep_browser_open=keep_open
                    )
                    
                    # 제외 패턴에 따라 링크 필터링
                    filtered_links = []
                    excluded_count = 0
                    
                    for link in links:
                        if self.should_exclude_link(link):
                            self.excluded_links.add(link)
                            excluded_count += 1
                        else:
                            filtered_links.append(link)
                    
                    before_count = len(self.all_links)
                    self.all_links.update(filtered_links)
                    new_count = len(self.all_links) - before_count
                    
                    print(f"새로운 링크 {new_count}개 추가 (중복 {len(filtered_links) - new_count}개 제거)")
                    if excluded_count > 0:
                        print(f"제외된 링크 {excluded_count}개 (패턴 매칭)")
                    print(f"현재 총 링크 수: {len(self.all_links)}")
                    
                except Exception as e:
                    print(f"검색 URL 처리 중 오류 발생: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        finally:
            # 모든 검색이 끝나면 브라우저 종료 (안전하게)
            try:
                self.crawler._close_browser()
            except Exception:
                pass  # 이미 종료되었을 수 있음
        
        return list(self.all_links)
    
    def save_links(self, filepath, links=None):
        """
        링크를 파일에 저장
        
        Args:
            filepath: 저장할 파일 경로
            links: 저장할 링크 리스트 (None이면 self.all_links 사용)
        """
        if links is None:
            links = list(self.all_links)
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        
        print(f"\n{len(links)}개 링크를 {filepath}에 저장했습니다.")
    
    def save_excluded_links(self, filepath):
        """
        제외된 링크를 별도 파일에 저장
        
        Args:
            filepath: 저장할 파일 경로
        """
        if not self.excluded_links:
            print("제외된 링크가 없습니다.")
            return
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        excluded_list = sorted(list(self.excluded_links))
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(excluded_list, f, ensure_ascii=False, indent=2)
        
        print(f"{len(excluded_list)}개 제외된 링크를 {filepath}에 저장했습니다.")
    
    def load_links(self, filepath):
        """
        파일에서 링크 로드
        
        Args:
            filepath: 로드할 파일 경로
            
        Returns:
            링크 리스트
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            links = json.load(f)
        
        self.all_links = set(links)
        print(f"{len(links)}개 링크를 {filepath}에서 로드했습니다.")
        return links


if __name__ == "__main__":
    # 테스트
    collector = LinkCollector(delay=1.0)
    
    # 여러 검색 URL 예시
    search_urls = [
        "https://www.google.com/search?q=python",
        "https://www.google.com/search?q=javascript",
    ]
    
    links = collector.collect_from_search_urls(search_urls, max_pages_per_search=2)
    print(f"\n총 {len(links)}개 고유 링크 수집 완료")
    
    # 저장
    collector.save_links("data/crawling/data/collected_links.json", links)
