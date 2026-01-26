# 구글 크롤링 도구

구글 검색 결과에서 링크를 수집하고, 수집한 링크에서 텍스트 내용을 추출하는 도구입니다.

## 요구사항

- **Python 3.9 이상** (Python 3.11 또는 3.12 권장)
  - Playwright는 Python 3.8+ 지원
  - 최신 기능과 성능 향상을 위해 Python 3.11 이상 사용 권장

## 설치

1. 패키지 설치:
```bash
pip install -r requirements.txt
```

2. Playwright 브라우저 설치 (필수):
```bash
# Windows에서는 python -m playwright 사용
# Chromium만 설치 (권장)
python -m playwright install chromium

# 또는 모든 브라우저 설치
python -m playwright install
```

**참고**: Windows PowerShell에서 `playwright` 명령어가 인식되지 않으면 `python -m playwright`를 사용하세요.

## 사용법

### 1. 링크 수집만 하기
```bash
python data/crawling/collect_links.py
```

**입력 방식:**
- JSON 파일에서 검색 URL을 읽어서 처리
- 실행 시 JSON 파일 경로 입력 (기본값: `data/crawling/data/search_urls.json`)

**예시 파일:**
- `data/crawling/data/search_urls_example.json` (JSON 형식 예시)

**결과:**
- 수집된 링크는 `data/crawling/data/collected_links.json`에 저장됩니다

### 2. 컨텐츠 추출만 하기
```bash
python data/crawling/extract_content.py
```
- 저장된 링크 파일에서 텍스트 내용 추출
- 결과는 `data/crawling/data/extracted_content.json`에 저장

### 3. 전체 프로세스 실행 (링크 수집 + 컨텐츠 추출)
```bash
python data/crawling/main.py
```
- 링크 수집과 컨텐츠 추출을 순차적으로 실행

## 데이터 저장 위치

모든 크롤링 데이터는 `data/crawling/data/` 폴더에 저장됩니다:
- `collected_links.json`: 수집된 링크 목록
- `extracted_content.json`: 추출된 텍스트 내용
- `search_urls_example.json`: 검색 URL 파일 예시

## 검색 URL 파일 형식

JSON 파일만 지원합니다. 다음 형식 중 하나를 사용하세요:

### 형식 1: 배열 형식
```json
[
  "https://www.google.com/search?q=python",
  "https://www.google.com/search?q=javascript"
]
```

### 형식 2: 객체 형식
```json
{
  "urls": [
    "https://www.google.com/search?q=python",
    "https://www.google.com/search?q=javascript"
  ]
}
```

## 주요 변경사항

### Playwright 사용
- **이전**: requests + BeautifulSoup4 (JavaScript 미지원)
- **현재**: Playwright (JavaScript 완전 지원, 실제 브라우저처럼 동작)

### 장점
- ✅ JavaScript로 동적 로드되는 콘텐츠 처리 가능
- ✅ 구글 봇 감지 우회 가능성 향상
- ✅ 실제 사용자처럼 동작하여 차단 위험 감소
- ✅ Selenium보다 빠르고 효율적

### 성능
- Playwright는 Selenium보다 약 2-3배 빠름
- 헤드리스 모드로 리소스 사용 최적화
