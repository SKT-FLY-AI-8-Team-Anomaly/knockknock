"""
구글 크롤링 전체 프로세스를 실행하는 메인 파일
(링크 수집과 컨텐츠 추출을 모두 실행)
"""
import sys
from pathlib import Path

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from link_collector import LinkCollector, load_search_urls_from_file
from content_extractor import ContentExtractor


def main():
    """
    전체 크롤링 프로세스 실행 (링크 수집 + 텍스트 추출)
    """
    print("=" * 60)
    print("구글 크롤링 전체 프로세스")
    print("=" * 60)
    
    # 1단계: 검색 URL JSON 파일 로드
    filepath = "data/crawling/data/search_urls.json"
    print(f"\n[1단계] 검색 URL 파일 로드: {filepath}")
    
    try:
        search_urls = load_search_urls_from_file(filepath)
        print(f"\n로드된 검색 URL 목록:")
        for i, url in enumerate(search_urls, 1):
            print(f"  {i}. {url}")
    except Exception as e:
        print(f"\n오류: {e}")
        return
    
    if not search_urls:
        print("검색 URL이 없습니다. 종료합니다.")
        return
    
    # 설정
    max_pages_per_search = int(input("\n각 검색당 최대 페이지 수 (기본값: 10): ").strip() or "10")
    delay = float(input("링크 수집 시 요청 간 대기 시간(초) (기본값: 1.0): ").strip() or "1.0")
    
    # 2단계: 링크 수집
    print("\n" + "=" * 60)
    print("[2단계] 링크 수집")
    print("=" * 60)
    
    collector = LinkCollector(delay=delay)
    links = collector.collect_from_search_urls(search_urls, max_pages_per_search=max_pages_per_search)
    
    # 링크 저장
    links_file = "data/crawling/data/collected_links.json"
    collector.save_links(links_file, links)
    
    # 3단계: 텍스트 추출
    print("\n" + "=" * 60)
    print("[3단계] 텍스트 내용 추출")
    print("=" * 60)
    
    extract_delay = float(input("\n텍스트 추출 시 요청 간 대기 시간(초) (기본값: 1.0): ").strip() or "1.0")
    extractor = ContentExtractor(delay=extract_delay)
    
    content_file = "data/crawling/data/extracted_content.json"
    results = extractor.extract_from_links(links, output_file=content_file)
    
    # 완료
    print("\n" + "=" * 60)
    print("크롤링 완료!")
    print("=" * 60)
    print(f"수집된 링크: {links_file}")
    print(f"추출된 텍스트: {content_file}")
    print(f"총 {len(links)}개 링크, {sum(1 for v in results.values() if v)}개 텍스트 추출 성공")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
