# knockknock

## 프로젝트 개요

이 프로젝트는 구글 검색 결과를 크롤링하여 링크를 수집하고, 수집한 링크에서 텍스트 내용을 추출하는 도구입니다.

## 빠른 시작

### 설치

1. 패키지 설치:
```bash
pip install -r requirements.txt
```

2. Playwright 브라우저 설치 (필수):
```bash
python -m playwright install chromium
```

### 사용법

```bash
# 링크 수집
python data/crawling/collect_links.py

# 컨텐츠 추출
python data/crawling/extract_content.py

# 전체 프로세스
python data/crawling/main.py
```

## 상세 문서

크롤링 도구에 대한 자세한 사용법과 설명은 [data/crawling/README.md](data/crawling/README.md)를 참조하세요.

## 데이터 저장 위치

모든 크롤링 데이터는 `data/crawling/data/` 폴더에 저장됩니다.
