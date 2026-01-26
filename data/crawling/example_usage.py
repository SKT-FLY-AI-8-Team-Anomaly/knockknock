"""
구글 크롤링 사용 예제
"""
import sys
from pathlib import Path

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from link_collector import LinkCollector
from content_extractor import ContentExtractor


def example_usage():
    """
    간단한 사용 예제
    """
    # 1. 여러 검색 URL에서 링크 수집
    print("=" * 60)
    print("예제: 구글 검색 링크 수집 및 텍스트 추출")
    print("=" * 60)
    
    # 검색 URL 리스트
    search_urls = [
        "https://www.google.com/search?q=python+tutorial",
        "https://www.google.com/search?q=web+scraping",
    ]
    
    # 링크 수집
    print("\n[1단계] 링크 수집 중...")
    collector = LinkCollector(delay=1.0)
    links = collector.collect_from_search_urls(
        search_urls, 
        max_pages_per_search=3  # 각 검색당 3페이지만
    )
    
    # 링크 저장
    links_file = "data/crawling/data/collected_links.json"
    collector.save_links(links_file, links)
    
    # 2. 수집한 링크에서 텍스트 추출
    print("\n[2단계] 텍스트 추출 중...")
    extractor = ContentExtractor(delay=1.0)
    results = extractor.extract_from_links(
        links[:5],  # 처음 5개만 테스트
        output_file="data/crawling/data/extracted_content.json"
    )
    
    print("\n완료!")


if __name__ == "__main__":
    example_usage()
