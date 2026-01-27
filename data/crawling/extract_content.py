"""
수집한 링크에서 텍스트 내용을 추출하는 스크립트
"""
import sys
import json
from pathlib import Path

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from content_extractor import ContentExtractor
from link_collector import load_exclude_patterns_from_file


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
    
    # 제외 패턴 로드
    exclude_patterns_file = "data/crawling/data/exclude_patterns.json"
    print(f"\n[제외 패턴 로드] {exclude_patterns_file}")
    exclude_patterns = load_exclude_patterns_from_file(exclude_patterns_file)
    
    # 제외 패턴 적용
    if exclude_patterns:
        original_count = len(links)
        links = [link for link in links if not any(pattern in link for pattern in exclude_patterns)]
        excluded_count = original_count - len(links)
        if excluded_count > 0:
            print(f"제외 패턴으로 {excluded_count}개 링크 제외됨")
    
    # 기존 추출 결과 로드 (중복 방지 및 재개)
    content_file = "data/crawling/data/extracted_content.json"
    existing_results = {}
    if Path(content_file).exists():
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
            print(f"\n기존 추출 결과 {len(existing_results)}개 발견 (이미 추출된 링크는 건너뜁니다)")
        except:
            print("\n기존 추출 결과 파일이 있지만 로드할 수 없습니다. 새로 시작합니다.")
    
    # 이미 추출된 링크 제외
    links_to_extract = [link for link in links if link not in existing_results or existing_results.get(link) is None]
    already_extracted = len(links) - len(links_to_extract)
    
    if already_extracted > 0:
        print(f"이미 추출된 링크 {already_extracted}개 건너뜁니다")
    
    if not links_to_extract:
        print("\n추출할 새로운 링크가 없습니다. 모든 링크가 이미 추출되었습니다.")
        return
    
    # 설정
    extract_delay = float(input("\n요청 간 대기 시간(초) (기본값: 1.0): ").strip() or "1.0")
    save_interval = int(input("중간 저장 간격 (N개마다 저장, 기본값: 10, 0이면 중간 저장 안함): ").strip() or "10")
    
    # 전체 링크 추출 여부 확인
    if len(links_to_extract) > 50:
        use_all = input(f"\n{len(links_to_extract)}개 링크를 모두 추출하시겠습니까? (y/n, 기본값: y): ").strip().lower() or "y"
        if use_all != 'y':
            max_links = int(input("추출할 링크 개수 (기본값: 10): ").strip() or "10")
            links_to_extract = links_to_extract[:max_links]
            print(f"{len(links_to_extract)}개 링크만 추출합니다.")
    
    # 텍스트 추출
    print("\n" + "=" * 60)
    print("[텍스트 추출 시작]")
    print("=" * 60)
    
    extractor = ContentExtractor(delay=extract_delay)
    
    # 새로 추출할 링크들 처리 (extract_from_links 내부에서 자동으로 기존 결과와 병합하여 저장)
    new_results = extractor.extract_from_links(links_to_extract, output_file=content_file, save_interval=save_interval)
    
    # 최종 결과 로드 (병합된 결과)
    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            all_results = json.load(f)
    except:
        all_results = {**existing_results, **new_results}
    
    # 완료
    print("\n" + "=" * 60)
    print("텍스트 추출 완료!")
    print("=" * 60)
    print(f"추출된 텍스트: {content_file}")
    new_success_count = sum(1 for v in new_results.values() if v is not None)
    total_success_count = sum(1 for v in all_results.values() if v is not None)
    print(f"이번 세션: {len(links_to_extract)}개 링크 중 {new_success_count}개 텍스트 추출 성공")
    print(f"전체 누적: {len(all_results)}개 링크 중 {total_success_count}개 텍스트 추출 성공")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
