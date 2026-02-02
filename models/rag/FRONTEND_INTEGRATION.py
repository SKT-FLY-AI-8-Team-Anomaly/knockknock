"""
프론트엔드에서 RAG API를 사용하는 방법 (React/TypeScript)
"""

# ============================================================================
# 1. API 클라이언트 생성 (TypeScript)
# ============================================================================

"""
// prototype/figma-code/src/utils/ragClient.ts

const RAG_API_BASE = process.env.REACT_APP_RAG_API_URL || "http://localhost:8000";

export interface RagDocument {
  id: string;
  text: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface ChatRequest {
  message: string;
  user_id?: string;
}

export interface ChatResponse {
  reply: string;
  context_docs?: number;
}

class RAGClient {
  private baseUrl: string;

  constructor(baseUrl: string = RAG_API_BASE) {
    this.baseUrl = baseUrl;
  }

  // RAG 문서 추가
  async addDocuments(texts: string[], metadata?: Record<string, unknown>) {
    const response = await fetch(`${this.baseUrl}/api/rag/add`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ texts, metadata }),
    });

    if (!response.ok) {
      throw new Error(`Failed to add documents: ${response.statusText}`);
    }

    return response.json();
  }

  // RAG 문서 목록 조회
  async listDocuments(): Promise<{ count: number; docs: RagDocument[] }> {
    const response = await fetch(`${this.baseUrl}/api/rag/list`);

    if (!response.ok) {
      throw new Error(`Failed to list documents: ${response.statusText}`);
    }

    return response.json();
  }

  // RAG 문서 모두 삭제
  async clearDocuments() {
    const response = await fetch(`${this.baseUrl}/api/rag/clear`, {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error(`Failed to clear documents: ${response.statusText}`);
    }

    return response.json();
  }

  // 채팅 (RAG 컨텍스트 포함)
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to chat: ${response.statusText}`);
    }

    return response.json();
  }

  // 문서 검색
  async search(query: string, limit: number = 4) {
    const params = new URLSearchParams({ q: query, limit: limit.toString() });
    const response = await fetch(`${this.baseUrl}/api/search?${params}`);

    if (!response.ok) {
      throw new Error(`Failed to search: ${response.statusText}`);
    }

    return response.json();
  }
}

export const ragClient = new RAGClient();
"""

# ============================================================================
# 2. React 컴포넌트 예제
# ============================================================================

"""
// prototype/figma-code/src/components/ChatbotPage.tsx

import { useState } from "react";
import { ragClient } from "../utils/ragClient";

export function ChatbotPage() {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);
  const [contextDocs, setContextDocs] = useState(0);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!message.trim()) return;

    setLoading(true);
    try {
      const response = await ragClient.chat({
        message: message,
        user_id: "user123", // 실제로는 로그인한 사용자 ID
      });

      setReply(response.reply);
      setContextDocs(response.context_docs || 0);
      setMessage("");
    } catch (error) {
      console.error("Chat error:", error);
      setReply("오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chatbot-page">
      <div className="chat-box">
        {reply && (
          <div className="bot-reply">
            <p>{reply}</p>
            {contextDocs > 0 && (
              <small className="context-info">
                ({contextDocs}개 문서 참고)
              </small>
            )}
          </div>
        )}
      </div>

      <form onSubmit={handleSendMessage} className="chat-form">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="질문을 입력하세요..."
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? "전송 중..." : "전송"}
        </button>
      </form>
    </div>
  );
}
"""

# ============================================================================
# 3. 문서 관리 컴포넌트 예제
# ============================================================================

"""
// prototype/figma-code/src/components/DocumentManager.tsx

import { useState, useEffect } from "react";
import { ragClient } from "../utils/ragClient";

export function DocumentManager() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const result = await ragClient.listDocuments();
      setDocuments(result.docs);
    } catch (error) {
      console.error("Failed to load documents:", error);
    }
  };

  const handleAddDocument = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const text = formData.get("text") as string;

    if (!text.trim()) return;

    setLoading(true);
    try {
      await ragClient.addDocuments([text]);
      await loadDocuments();
      e.currentTarget.reset();
    } catch (error) {
      console.error("Failed to add document:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleClearAll = async () => {
    if (window.confirm("모든 문서를 삭제하시겠습니까?")) {
      try {
        await ragClient.clearDocuments();
        setDocuments([]);
      } catch (error) {
        console.error("Failed to clear documents:", error);
      }
    }
  };

  return (
    <div className="document-manager">
      <h2>RAG 문서 관리</h2>

      <form onSubmit={handleAddDocument} className="add-document-form">
        <textarea
          name="text"
          placeholder="문서 내용을 입력하세요..."
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? "추가 중..." : "문서 추가"}
        </button>
      </form>

      <div className="documents-list">
        <h3>저장된 문서 ({documents.length})</h3>
        {documents.map((doc) => (
          <div key={doc.id} className="document-item">
            <p>{doc.text.substring(0, 100)}...</p>
            <small>{new Date(doc.created_at).toLocaleString("ko-KR")}</small>
          </div>
        ))}
      </div>

      {documents.length > 0 && (
        <button onClick={handleClearAll} className="clear-button">
          모든 문서 삭제
        </button>
      )}
    </div>
  );
}
"""

# ============================================================================
# 4. 환경 변수 설정 (.env.local)
# ============================================================================

"""
// prototype/figma-code/.env.local

REACT_APP_RAG_API_URL=http://localhost:8000
"""

# ============================================================================
# 5. 빌드 및 실행
# ============================================================================

# RAG API 서버 실행
# cd models/rag
# pip install -r requirements.txt
# python server.py

# 또는 OPENAI_API_KEY 환경 변수와 함께 실행
# OPENAI_API_KEY=sk-... python server.py

# 프로덕션 환경 (gunicorn)
# gunicorn -w 4 -b 0.0.0.0:8000 server:app

# ============================================================================
# 6. Docker 배포 (선택사항)
# ============================================================================

"""
# models/rag/Dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["python", "server.py"]
"""

# ============================================================================
# 7. API 엔드포인트 요약
# ============================================================================

"""
기본 URL: http://localhost:8000

1. 문서 추가
   POST /api/rag/add
   Body: { "texts": ["문서1", "문서2"], "metadata": {...} }
   Response: { "success": true, "count": 2 }

2. 문서 목록
   GET /api/rag/list
   Response: { "count": 2, "docs": [...] }

3. 문서 삭제
   POST /api/rag/clear
   Response: { "success": true }

4. 채팅 (RAG)
   POST /api/chat
   Body: { "message": "질문...", "user_id": "user123" }
   Response: { "reply": "답변...", "context_docs": 2 }

5. 검색
   GET /api/search?q=검색어&limit=4
   Response: { "query": "검색어", "count": 2, "documents": [...] }

6. 헬스체크
   GET /health
   Response: { "status": "ok" }

7. 설정 조회
   GET /api/config
   Response: { "openai_model": "gpt-4-turbo", ... }
"""
