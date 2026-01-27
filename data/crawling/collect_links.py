"""
구글 검색에서 링크를 수집하는 스크립트
"""
import sys
from pathlib import Path

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from link_collector import LinkCollector, load_search_urls_from_file, load_exclude_patterns_from_file


def main():
    """
    링크 수집 프로세스 실행
    """
    print("=" * 60)
    print("구글 검색 링크 수집")
    print("=" * 60)
    
    # 검색 URL JSON 파일 로드
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
    
    # 제외 패턴 로드
    exclude_patterns_file = "data/crawling/data/exclude_patterns.json"
    print(f"\n[1-2단계] 제외 패턴 파일 로드: {exclude_patterns_file}")
    exclude_patterns = load_exclude_patterns_from_file(exclude_patterns_file)
    
    # 설정
    max_pages_per_search = int(input("\n각 검색당 최대 페이지 수 (기본값: 10): ").strip() or "10")
    delay = float(input("요청 간 대기 시간(초) (기본값: 1.0): ").strip() or "1.0")
    
    # 헤드리스 모드 선택 (캡차 우회를 위해)
    headless_input = input("헤드리스 모드 사용? (y/n, 기본값: y, 캡차 시 n 권장): ").strip().lower() or "y"
    headless = headless_input == "y"
    
    if not headless:
        print("  ⚠️ 헤드리스 모드가 꺼져있습니다. 브라우저 창이 열립니다.")
        print("  캡차가 나타나면 수동으로 해결해주세요.")
    
    # 링크 수집
    print("\n" + "=" * 60)
    print("[2단계] 링크 수집")
    print("=" * 60)
    
    collector = LinkCollector(delay=delay, headless=headless, exclude_patterns=exclude_patterns)
    links = collector.collect_from_search_urls(search_urls, max_pages_per_search=max_pages_per_search)
    
    # 링크 저장
    links_file = "data/crawling/data/collected_links.json"
    collector.save_links(links_file, links)
    
    # 제외된 링크 저장 (제외된 링크가 있는 경우)
    if collector.excluded_links:
        excluded_links_file = "data/crawling/data/excluded_links.json"
        collector.save_excluded_links(excluded_links_file)
    
    # 완료
    print("\n" + "=" * 60)
    print("링크 수집 완료!")
    print("=" * 60)
    print(f"수집된 링크: {links_file}")
    print(f"총 {len(links)}개 링크 수집 완료")
    if collector.excluded_links:
        print(f"제외된 링크: {len(collector.excluded_links)}개")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
