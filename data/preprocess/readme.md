# AI Real Estate Document OCR Converter (부동산 문서 AI OCR)

이 프로젝트는 **OpenAI GPT-4o**의 Vision 기능을 활용하여 PDF 형식의 부동산 문서를 **구조화된 Markdown** 텍스트로 변환하는 Python 스크립트입니다.

단순한 텍스트 추출을 넘어, 복잡한 표 레이아웃을 서술형으로 변환하고, 민감한 개인정보(주민등록번호 뒷자리)를 마스킹하며, 긴 문서를 배치(Batch) 단위로 나누어 처리합니다.

## ✨ 주요 기능

* **PDF to Image 변환**: `pdf2image`를 사용하여 PDF의 각 페이지를 고해상도 이미지로 변환합니다.
* **Batch Processing**: 긴 문서를 지정된 페이지 수(기본 3장)만큼 묶어서 처리하여 API 오류를 방지하고 처리 안정성을 높입니다.
* **GPT-4o Vision 활용**: 최신 멀티모달 모델을 사용하여 텍스트, 표, 특약 사항을 정확하게 인식합니다.
* **할루시네이션 방지 & 포맷팅**:
    * 표(Table) 깨짐 방지를 위해 리스트 형태로 풀어서 변환
    * 판독 불가능한 글자는 억지로 추측하지 않고 `(판독불가)` 처리
    * 주민등록번호 뒷자리 마스킹 (`******`)
* **자동 저장**: 변환된 결과는 원본 파일명과 동일한 `.md` 파일로 저장됩니다.

## 🛠️ 사전 요구 사항 (Prerequisites)

이 코드를 실행하기 위해서는 **Poppler**가 시스템에 설치되어 있어야 합니다. (`pdf2image` 라이브러리 의존성)

### Poppler 설치 방법
* **Windows**: [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) 다운로드 후 `bin` 폴더를 시스템 환경변수 `PATH`에 추가
* **Mac (Homebrew)**: `brew install poppler`
* **Linux (Ubuntu)**: `sudo apt-get install poppler-utils`

### .env 파일
```
OPENAI_API_KEY=sk-your-api-key-here...
```

## 사용 방법(Usage)
기본 실행
```bash
python main.py --pdf_path "문서경로/부동산계약서.pdf" --batch_size 3
```