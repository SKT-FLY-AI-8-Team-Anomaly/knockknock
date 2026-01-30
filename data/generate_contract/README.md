# 🏠 주택임대차표준계약서 합성 데이터 생성기 (Synthetic Contract Generator)

LLM(GPT-4o 등)을 활용하여 **대한민국 주택임대차표준계약서** 형식의 가상 데이터를 생성하는 도구입니다.
**정상(Normal)** 계약서뿐만 아니라, 의도적인 논리 오류나 독소 조항이 포함된 **비정상(Anomaly)** 계약서를 생성하여 AI 모델 학습(이상 탐지, RAG)용 데이터셋을 구축할 수 있습니다.

## ✨ 주요 기능

* **고품질 데이터 생성**: LLM을 통해 실제와 유사한 주소, 인명, 특약사항을 생성합니다.
* **비정상(Anomaly) 데이터 생성**: 학습용 데이터 확보를 위해 6가지 유형의 정교한 오류를 무작위로 주입합니다.
    * 금액 합산 오류 (보증금 != 계약금 + 잔금)
    * 날짜 논리 오류 (잔금일 역전, 계약 기간 오류 등)
    * 주민등록번호 형식 위반
    * 중개보수 과다 청구
    * **독소 조항(Toxic Clauses)** 포함 (임차인에게 치명적인 불공정 특약)
* **자동 검증 (Validation)**: Python 코드로 금액, 날짜, 포맷의 정합성을 2차 검증합니다.
* **이중 출력 포맷**:
    * `docx`: 실제 사람이 보는 **MS Word 계약서 파일**
    * `json`: 학습 데이터 라벨링을 위한 **메타데이터 파일** (`is_anomaly`, `anomaly_category` 등 포함)

## 📦 설치 방법 (Installation)
### 1. 필수 라이브러리 설치
```bash
pip install langchain-openai langchain-community docxtpl pydantic python-dotenv python-dateutil langgraph
```

### 2. 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 OpenAI API 키를 입력하세요.
```bash
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. 템플릿 준비
`data` 폴더 내에 `주택임대차표준계약서.docx` 템플릿 파일이 위치해야 합니다. (워드 템플릿 내 변수는 `{{ variable }}` 형식으로 작성되어 있어야 함)


### 4. 사용 방법
#### 기본 실행 (5개 생성)
```bash
python gen_fake_contract.py
```

#### 옵션 지정 실행
```bash
python gen_fake_contract.py --count 100 --output_dir "./dataset/train"
```

## 📝 인자 (Arguments) 설명

| 인자 | 설명 | 기본값 |
|------|------|--------|
| `--count` | 생성할 계약서의 개수 | 5 |
| `--output_dir` | 결과 파일이 저장될 폴더 경로 | `./data/output` |
| `--template_path` | 워드 템플릿 파일 경로 | `./data/주택임대차표준계약서.docx` |

## 📂 출력 결과물 구조

`output_dir`에 다음과 같이 Word 파일과 JSON 파일이 쌍으로 생성됩니다.

```
data/
└── normal/
    ├── contract_1.docx       # 정상 계약서 (문서)
    ├── contract_1.json       # 정상 계약서 라벨 (JSON)
    └── ...
└── anomaly/
    ├── contract_1.docx      # 비정상 계약서 (문서)
    ├── contract_1.json      # 비정상 계약서 라벨 (JSON)
    └── ...
```

## 📊 JSON 라벨링 예시

`contract_2_anomaly.json`
```json
{
    "filename": "contract_2_anomaly.docx",
    "is_anomaly": true,
    "anomaly_category": "날짜 역전 오류",
    "anomaly_description": "잔금 지급일(입주일)을 계약일보다 3일 이전인 과거 날짜로 설정함",
    "validation_errors_detected": [
        "[날짜 오류] 계약일(2024-05-10)이 잔금일(2024-05-07)보다 미래입니다."
    ],
}
```

## 🛠️ 기술 스택

* **Language**: Python 3.10+
* **LLM**: OpenAI GPT-5.2 (Structured Output)
* **Validation**: Pydantic, Python datetime logic
* **Document**: docxtpl (Jinja2 syntax support)
