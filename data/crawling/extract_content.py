"""
수집한 링크에서 텍스트 내용을 추출하는 스크립트
"""
import sys
import json
from pathlib import Path

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from content_extractor import ContentExtractor


def main():
    """
    텍스트 추출 프로세스 실행
    """
    print("=" * 60)
    print("링크에서 텍스트 내용 추출")
    print("=" * 60)
    
    # 링크 파일 경로 입력
    links_file = input("\n링크 파일 경로 (기본값: data/crawling/data/collected_links.json): ").strip() or "data/crawling/data/collected_links.json"
    
    # 링크 파일 로드
    try:
        links_path = Path(links_file)
        if not links_path.exists():
            print(f"오류: 파일을 찾을 수 없습니다: {links_file}")
            return
        
        with open(links_path, 'r', encoding='utf-8') as f:
            links = json.load(f)
        
        if not links:
            print("오류: 링크가 없습니다.")
            return
        
        print(f"{len(links)}개 링크를 로드했습니다.")
        
    except json.JSONDecodeError:
        print(f"오류: JSON 파일 형식이 올바르지 않습니다: {links_file}")
        return
    except Exception as e:
        print(f"오류: 파일 로드 실패: {e}")
        return
    
    # 설정
    extract_delay = float(input("\n요청 간 대기 시간(초) (기본값: 1.0): ").strip() or "1.0")
    
    # 전체 링크 추출 여부 확인
    use_all = input("\n모든 링크를 추출하시겠습니까? (y/n, 기본값: y): ").strip().lower() or "y"
    
    if use_all == 'y':
        links_to_extract = links
    else:
        max_links = int(input("추출할 링크 개수 (기본값: 10): ").strip() or "10")
        links_to_extract = links[:max_links]
        print(f"{len(links_to_extract)}개 링크만 추출합니다.")
    
    # 텍스트 추출
    print("\n" + "=" * 60)
    print("[텍스트 추출 시작]")
    print("=" * 60)
    
    extractor = ContentExtractor(delay=extract_delay)
    
    content_file = "data/crawling/data/extracted_content.json"
    results = extractor.extract_from_links(links_to_extract, output_file=content_file)
    
    # 완료
    print("\n" + "=" * 60)
    print("텍스트 추출 완료!")
    print("=" * 60)
    print(f"추출된 텍스트: {content_file}")
    success_count = sum(1 for v in results.values() if v is not None)
    print(f"총 {len(links_to_extract)}개 링크 중 {success_count}개 텍스트 추출 성공")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
