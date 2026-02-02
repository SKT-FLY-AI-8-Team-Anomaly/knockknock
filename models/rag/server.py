"""
RAG FastAPI Server
웹 애플리케이션과 통신하는 RAG API 서버
"""

import os
import json
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import logging

from rag_core import RAGManager, RagDoc, IRAGStore
from openai_service import OpenAIService
from dotenv import load_dotenv

# 로깅 설정
_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(_ENV_PATH)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Pydantic 모델
# ============================================================================


class AddDocumentRequest(BaseModel):
    texts: List[str]
    metadata: Optional[dict] = None


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    text: str
    metadata: Optional[dict] = None
    created_at: str


class AddDocumentResponse(BaseModel):
    success: bool
    count: int


class ListDocumentResponse(BaseModel):
    count: int
    docs: List[DocumentResponse]


class ChatResponse(BaseModel):
    reply: str
    context_docs: Optional[int] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# ============================================================================
# 마크다운 파일 기반 스토리지
# ============================================================================


class MarkdownFileStore(IRAGStore):
    """마크다운 파일 기반 RAG 문서 저장소"""

    def __init__(self, directory: str = "rag_documents"):
        self.directory = directory
        self.ensure_directory_exists()
        self.metadata_file = os.path.join(directory, ".metadata.json")

    def ensure_directory_exists(self):
        """디렉토리가 없으면 생성"""
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            logger.info(f"Created RAG documents directory: {self.directory}")

    async def get_rag_docs(self) -> list[RagDoc]:
        """디렉토리의 모든 마크다운 파일 로드"""
        try:
            docs = []
            
            # 메타데이터 로드
            metadata_map = {}
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    metadata_map = json.load(f)
            
            # 모든 마크다운 파일 읽기
            for filename in os.listdir(self.directory):
                if filename.endswith(".md") and filename != ".metadata":
                    filepath = os.path.join(self.directory, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # 파일명에서 ID 생성
                        doc_id = filename[:-3]  # .md 제거
                        
                        # 메타데이터 가져오기
                        meta = metadata_map.get(doc_id, {})
                        
                        # RagDoc 생성
                        doc = RagDoc(
                            id=doc_id,
                            text=content,
                            embedding=meta.get("embedding", []),
                            metadata=meta.get("metadata"),
                            created_at=meta.get("created_at", "")
                        )
                        docs.append(doc)
                    except Exception as e:
                        logger.warning(f"Error loading {filename}: {e}")
            
            return docs
        except Exception as e:
            logger.warning(f"Error loading RAG documents: {e}")
            return []

    async def save_rag_docs(self, docs: list[RagDoc]) -> None:
        """마크다운 파일로 저장"""
        try:
            # 메타데이터 저장용 딕셔너리
            metadata_map = {}
            
            for doc in docs:
                # 마크다운 파일로 저장 (본문만)
                filepath = os.path.join(self.directory, f"{doc.id}.md")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(doc.text)
                
                # 메타데이터 저장
                metadata_map[doc.id] = {
                    "embedding": doc.embedding,
                    "metadata": doc.metadata,
                    "created_at": doc.created_at
                }
            
            # 메타데이터를 JSON으로 저장
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata_map, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(docs)} RAG documents to {self.directory}")
        except Exception as e:
            logger.error(f"Error saving RAG documents: {e}")
            raise


# ============================================================================
# Azure Blob Storage 기반 스토리지
# ============================================================================


class AzureBlobStore(IRAGStore):
    """Azure Blob Storage 기반 RAG 문서 저장소"""

    def __init__(self, connection_string: str, container_name: str):
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ImportError("azure-storage-blob is required for AzureBlobStore")
        
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        self.container_client = self.blob_service_client.get_container_client(
            container_name
        )
        self.metadata_blob_name = ".metadata.json"

    async def get_rag_docs(self) -> list[RagDoc]:
        """Azure Blob Storage에서 마크다운 문서 로드"""
        try:
            docs = []
            
            # 메타데이터 로드
            metadata_map = {}
            try:
                metadata_blob = self.container_client.get_blob_client(
                    self.metadata_blob_name
                )
                metadata_content = metadata_blob.download_blob().readall()
                metadata_map = json.loads(metadata_content.decode("utf-8"))
            except Exception as e:
                logger.warning(f"Error loading metadata: {e}")
            
            # 모든 블롭 나열
            blobs = self.container_client.list_blobs()
            
            for blob in blobs:
                # 메타데이터 파일과 숨김 파일 제외
                if blob.name.startswith(".") or blob.name.endswith(".json"):
                    continue
                
                if not blob.name.endswith(".md"):
                    continue
                
                try:
                    # 파일명에서 ID 생성
                    doc_id = blob.name[:-3]  # .md 제거
                    
                    # 블롭 다운로드
                    blob_client = self.container_client.get_blob_client(blob.name)
                    content = blob_client.download_blob().readall()
                    text = content.decode("utf-8")
                    
                    # 메타데이터 가져오기
                    meta = metadata_map.get(doc_id, {})
                    
                    # RagDoc 생성
                    doc = RagDoc(
                        id=doc_id,
                        text=text,
                        embedding=meta.get("embedding", []),
                        metadata=meta.get("metadata"),
                        created_at=meta.get("created_at", "")
                    )
                    docs.append(doc)
                except Exception as e:
                    logger.warning(f"Error loading {blob.name}: {e}")
            
            logger.info(f"Loaded {len(docs)} documents from Azure Blob Storage")
            return docs
        except Exception as e:
            logger.warning(f"Error loading RAG documents from Azure: {e}")
            return []

    async def save_rag_docs(self, docs: list[RagDoc]) -> None:
        """마크다운 문서를 Azure Blob Storage에 저장"""
        try:
            # 메타데이터 저장용 딕셔너리
            metadata_map = {}
            
            for doc in docs:
                # 마크다운 파일로 업로드 (본문만)
                blob_name = f"{doc.id}.md"
                blob_client = self.container_client.get_blob_client(blob_name)
                blob_client.upload_blob(
                    doc.text.encode("utf-8"),
                    overwrite=True
                )
                
                # 메타데이터 저장
                metadata_map[doc.id] = {
                    "embedding": doc.embedding,
                    "metadata": doc.metadata,
                    "created_at": doc.created_at
                }
            
            # 메타데이터를 JSON으로 업로드
            metadata_blob = self.container_client.get_blob_client(
                self.metadata_blob_name
            )
            metadata_json = json.dumps(metadata_map, ensure_ascii=False, indent=2)
            metadata_blob.upload_blob(
                metadata_json.encode("utf-8"),
                overwrite=True
            )
            
            logger.info(f"Saved {len(docs)} RAG documents to Azure Blob Storage")
        except Exception as e:
            logger.error(f"Error saving RAG documents to Azure: {e}")
            raise


# ============================================================================
# FastAPI 앱 설정
# ============================================================================

app = FastAPI(
    title="RAG API Server",
    description="부동산 RAG 챗봇 API",
    version="1.0.0",
)

# CORS 설정 - 프론트엔드에서 접근 가능하도록
# Optional Entra auth (disabled by default)
AUTH_BYPASS_PATHS = {"/health", "/api/config"}


def _auth_enabled() -> bool:
    return os.getenv("RAG_AUTH_ENABLED", "false").lower() in ("1", "true", "yes", "on")


def _load_auth_settings() -> dict[str, str]:
    settings = {
        "issuer": os.getenv("ENTRA_ISSUER", ""),
        "audience": os.getenv("ENTRA_AUDIENCE", ""),
        "jwks_url": os.getenv("ENTRA_JWKS_URL", ""),
    }
    missing = [k for k, v in settings.items() if not v]
    if missing:
        raise ValueError(f"Missing auth settings: {', '.join(missing)}")
    return settings


@lru_cache(maxsize=1)
def _get_jwk_client(jwks_url: str):
    try:
        from jwt import PyJWKClient  # lazy import to avoid hard dependency at startup
    except Exception as exc:
        raise RuntimeError("PyJWT is required when RAG_AUTH_ENABLED=true") from exc
    return PyJWKClient(jwks_url)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    if not _auth_enabled() or request.url.path in AUTH_BYPASS_PATHS:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    token = auth_header.split(" ", 1)[1].strip()
    try:
        settings = _load_auth_settings()
        jwk_client = _get_jwk_client(settings["jwks_url"])
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        import jwt
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings["audience"],
            issuer=settings["issuer"],
        )
        request.state.user = claims
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    return await call_next(request)

# CORS 설정 - 프론트엔드에서 접근 가능하도록
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# RAG 서비스 초기화
# ============================================================================


async def get_rag_manager():
    """RAG 매니저 인스턴스 반환 (저장소 선택 가능)"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    # 저장소 선택: Azure 또는 로컬 파일시스템
    storage_type = os.getenv("RAG_STORAGE_TYPE", "local").lower()
    
    if storage_type == "azure":
        # Azure Blob Storage
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.getenv("AZURE_CONTAINER_NAME")
        
        if not connection_string or not container_name:
            raise HTTPException(
                status_code=500,
                detail="AZURE_STORAGE_CONNECTION_STRING and AZURE_CONTAINER_NAME are required for Azure storage"
            )
        
        store = AzureBlobStore(connection_string, container_name)
        logger.info("Using Azure Blob Storage for RAG documents")
    else:
        # 로컬 마크다운 파일 저장소 (기본값)
        store = MarkdownFileStore(
            os.getenv("RAG_DOCUMENTS_PATH", "rag_documents")
        )
        logger.info("Using local file storage for RAG documents")
    
    embedding_service = OpenAIService(
        api_key,
        embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ),
        chat_model=os.getenv("OPENAI_MODEL", "gpt-5.2"),
    )
    top_k = int(os.getenv("RAG_TOP_K", "4"))

    return RAGManager(store, embedding_service, top_k)


# ============================================================================
# 헬스체크
# ============================================================================


@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "ok", "message": "RAG API Server is running"}


# ============================================================================
# RAG 문서 관리 엔드포인트
# ============================================================================


@app.post("/api/rag/add", response_model=AddDocumentResponse)
async def add_documents(request: AddDocumentRequest):
    """
    새로운 문서를 RAG 시스템에 추가
    
    요청:
    ```json
    {
        "texts": ["문서1", "문서2"],
        "metadata": {"source": "value"}
    }
    ```
    """
    try:
        if not request.texts:
            raise HTTPException(status_code=400, detail="텍스트가 필요합니다")

        rag_manager = await get_rag_manager()
        result = await rag_manager.add_documents(request.texts, request.metadata)
        logger.info(f"Added {result['count']} documents")
        return AddDocumentResponse(success=result["success"], count=result["count"])

    except Exception as e:
        logger.error(f"Error adding documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/list", response_model=ListDocumentResponse)
async def list_documents():
    """
    저장된 모든 RAG 문서 조회
    """
    try:
        rag_manager = await get_rag_manager()
        docs = await rag_manager.get_all_documents()

        return ListDocumentResponse(
            count=len(docs),
            docs=[
                DocumentResponse(
                    id=doc.id,
                    text=doc.text,
                    metadata=doc.metadata,
                    created_at=doc.created_at,
                )
                for doc in docs
            ],
        )
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/clear")
async def clear_documents():
    """
    모든 RAG 문서 삭제
    """
    try:
        rag_manager = await get_rag_manager()
        await rag_manager.clear_documents()
        logger.info("Cleared all RAG documents")
        return {"success": True, "message": "모든 문서가 삭제되었습니다"}
    except Exception as e:
        logger.error(f"Error clearing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 채팅 엔드포인트 (RAG 통합)
# ============================================================================


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    부동산 챗봇과 대화 (RAG 컨텍스트 포함)
    
    요청:
    ```json
    {
        "message": "서울 주택 가격은 어떻게 되나요?",
        "user_id": "user123"
    }
    ```
    """
    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="메시지가 필요합니다")

        rag_manager = await get_rag_manager()
        embedding_service = rag_manager.embedding_service

        # 관련 문서 검색
        logger.info(f"Processing message: {request.message}")
        retrieved_docs = await rag_manager.retrieve_documents(request.message)
        context = rag_manager.format_context(retrieved_docs)

        # 시스템 프롬프트
        system_prompt = (
            """
            [ROLE / IDENTITY]
너는 '부동산 거래 안전 도우미' 챗봇이다. 사용자가 집을 구하고(전세/월세/매매), 계약을 준비하고, 분쟁을 예방하도록 돕는다.
너의 강점은 공인중개사 시험 범위 수준의 실무 지식(거래 절차, 서류, 권리관계, 분쟁 포인트, 특약 설계, 협상 포인트)에 기반한 설명이다.
다만 너는 변호사/공인중개사가 아니며 최종 법률 자문이나 확정적 판단을 제공하지 않는다.

[PRIMARY GOALS]
1) 사용자의 상황을 빠르게 파악하고, 거래 리스크를 낮추는 행동을 안내한다.
2) 질문에 답하되, '실제로 도움이 되는 다음 행동'과 '체크리스트/특약 문구 예시/협상 문장'까지 제공한다.
3) 모르는 것은 모른다고 말하고, 확인이 필요한 항목(서류/수치/지역 규정)은 사용자에게 확인 방법을 제시한다.
4) 사용자가 다른 탭(임장/서류 확인/계약 전 최종 확인)에서 할 수 있는 후속 조치를 자연스럽게 연결한다.

[DATA & GROUNDING]
- 너의 지식은 다음 범주의 내부 데이터에 기반한다:
  a) 전문가 의견(유튜브 자막 기반 요약/정리 데이터)
  b) 공인중개사 시험 교재 기반 정리 데이터
  c) 부동산 거래 관련 법/제도 요약 데이터
  d) 특약 조항 라이브러리(조항 + 필요한 이유 + 분쟁 사례 + 대안 문구)
- 내부 데이터에 '없거나 불확실한 내용'은 추측하지 말고, 확인 질문 또는 확인 방법을 제시한다.
- 특정 지역/시점에 따라 달라질 수 있는 제도/세율/대출/정책은 “변동 가능”으로 표시하고 최신 확인을 권한다.

[PRIVACY / SECURITY (매우 중요)]
- 사용자의 개인정보(주민번호, 계좌번호, 신분증 사진, 정확한 주소 전체, 계약서 원본 텍스트 전체 등)를 요구하지 않는다.
- 사용자가 민감정보를 입력하면, 즉시 '필요한 최소 정보만' 남기도록 안내하고 민감정보는 입력하지 말라고 경고한다.
- 주민번호/계좌/서명/신분증 등 민감정보가 포함된 문장이나 텍스트가 들어오면, 답변에서 그대로 반복하지 말고 '(민감정보는 마스킹/삭제 권장)'로 처리한다.
- 불법적인 접근(타인 서류 열람/위조/사문서 위조/편법 조회/공식 인증 우회 등) 요청은 거절하고 합법적 대안을 안내한다.

[SAFETY / REFUSAL RULES]
다음 요청은 정중히 거절한다:
- 서류 위조, 신분증/계약서 위조, 타인 개인정보 조회, 불법 녹취/감청, 법망 회피 조언
- 특정 개인/업체 비방을 위한 허위 주장 생성
거절 시에도 사용자가 할 수 있는 '합법적 대안(예: 공식 발급 경로, 중개사/변호사 상담 포인트, 필요한 체크리스트)'을 제공한다.

[INTERACTION STYLE]
- 기본 언어: 한국어. (사용자가 다른 언어를 쓰면 그 언어로 전환)
- 말투: 친절하고 단정하게. 과장 금지.
- 질문이 모호하면, '최소 2개, 최대 5개'만 핵심 확인 질문을 한 뒤 답변을 이어간다.
- 사용자가 초보자라고 가정하고, 용어는 짧게 정의한다(예: 근저당, 전입신고, 확정일자, 대항력 등).
- 답변은 항상 '실행 가능한 형태'로: 체크리스트, 단계, 문구 예시, 위험 신호(레드플래그) 제공.

[OUTPUT FORMAT (권장)]
가능하면 아래 구조를 지켜라.

1) 한 줄 요약: 사용자의 질문에 대한 결론/방향
2) 핵심 설명: 왜 그런지 + 리스크 포인트(중요도 순)
3) 지금 당장 할 일(체크리스트 3~7개)
4) 필요하면 제공:
   - 특약 제안: (조항 예시 문구) + (왜 필요한지) + (협상 포인트) + (주의/예외)
   - 집주인/중개사에게 물어볼 질문 예시(3~5개)
5) 추천 질문(미리보기) 3개:
   - '자주하는 질문(FAQ)' 3개 또는
   - '예상 질문(Next)' 3개
   (대화 맥락에 맞춰 자동 생성)

[DOMAIN BEHAVIOR GUIDELINES]
- 사용자가 '전세/월세/매매' 중 무엇인지 먼저 확인한다(이미 언급되었으면 생략).
- 아래 주제에 대해서는 특히 '레드플래그'를 명확히 제시한다:
  • 전세: 보증금 회수(선순위 권리/근저당/전세가율/깡통전세 위험), 대항력/확정일자, 보증보험 가능성
  • 월세: 관리비 항목, 수리 책임 범위, 원상복구 분쟁, 중도해지/위약금
  • 매매: 등기/권리관계, 하자담보책임, 잔금/명도 일정
- 하자/임장 관련 질문이면:
  • '사진/증거 확보 방식', '분쟁 줄이는 커뮤니케이션', '특약으로 남기는 방법' 중심으로 답하라.
  • 단, 사용자가 사진을 올리지 않았다면 사진 요구 대신 '촬영 체크리스트'를 먼저 준다.
- 계약서/특약 질문이면:
  • 불리한 조항 패턴(임차인 일방 부담, 포괄적 손해배상, 수리 책임 전가, 중개보수 전가 등)을 탐지해 설명한다.
  • 대안 문구(수정 제안)를 항상 함께 제시한다.
- 사용자가 불안/초조해 보이면:
  • '협상 시 한 문장 템플릿'과 '최소 확인해야 할 3가지'를 우선 제공해 안정을 돕는다.

[TOOL / APP FLOW AWARENESS]
너는 다음 화면으로 연결되는 후속 조치를 제안할 수 있다:
- 임장(4.2): 체크리스트 기반 촬영 → 하자 분석/해결/특약 추천
- 서류 확인(4.3): 등기부등본/토지대장 기반 위험 요소 점검
- 계약 전 최종 확인(4.4): 계약서 스캔/OCR → 개인정보 자동 제거 → 조항 분석 및 특약 반영
단, '버튼 누르세요' 같은 UI 지시를 장황하게 하지 말고, 사용자가 무엇을 얻는지(목적) 중심으로 짧게 안내한다.

[DEFAULT FIRST MESSAGE (사용자가 그냥 들어왔을 때)]
'지금 어떤 계약을 준비 중이신가요? (전세/월세/매매) 그리고 지역/예산/입주 희망 시기, 가장 걱정되는 점 1가지만 알려주시면 위험 포인트부터 정리해드릴게요. 민감정보(주민번호/계좌/신분증)는 입력하지 마세요.'
"""
        )

        # 응답 생성
        reply = await embedding_service.generate_response(
            system_prompt=system_prompt,
            user_message=request.message,
            rag_context=context if context else None,
        )

        logger.info(f"Generated response, context docs: {len(retrieved_docs)}")
        return ChatResponse(reply=reply, context_docs=len(retrieved_docs))

    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 검색 전용 엔드포인트
# ============================================================================


@app.get("/api/search")
async def search(q: str, limit: int = 4):
    """
    쿼리로 관련 문서 검색
    
    쿼리 파라미터:
    - q: 검색 쿼리
    - limit: 반환할 문서 수 (기본값: 4)
    """
    try:
        if not q:
            raise HTTPException(status_code=400, detail="검색 쿼리가 필요합니다")

        rag_manager = await get_rag_manager()
        rag_manager.set_top_k(limit)
        docs = await rag_manager.retrieve_documents(q)

        return {
            "query": q,
            "count": len(docs),
            "documents": [
                {
                    "id": doc.id,
                    "text": doc.text[:200] + "..." if len(doc.text) > 200 else doc.text,
                    "created_at": doc.created_at,
                }
                for doc in docs
            ],
        }
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 유틸리티
# ============================================================================


@app.get("/api/config")
async def get_config():
    """
    현재 설정 조회 (디버깅용)
    """
    storage_type = os.getenv("RAG_STORAGE_TYPE", "local")
    
    config = {
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
        "embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        "rag_top_k": int(os.getenv("RAG_TOP_K", "4")),
        "storage_type": storage_type,
    }
    
    # 저장소 타입별 추가 정보
    if storage_type == "azure":
        config["azure_container"] = os.getenv("AZURE_CONTAINER_NAME")
    else:
        config["documents_path"] = os.getenv("RAG_DOCUMENTS_PATH", "rag_documents")
    
    return config


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
