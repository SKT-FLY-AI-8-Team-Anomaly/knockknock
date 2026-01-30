#!/usr/bin/env python3
"""
Semantic deduplication for large markdown files using OpenAI embeddings.

Usage:
  python scripts/dedupe_semantic.py input1.md [input2.md ...] \
    --merge --output-dir cleaned --threshold 0.90

Requirements:
  - Set environment variable OPENAI_API_KEY
  - Install dependencies from requirements.txt (uses `openai`)

This script preserves original content but removes semantically near-duplicate
chunks (based on a cosine similarity threshold) to produce RAG-ready outputs.
"""
from __future__ import annotations
import argparse
import os
import math
from pathlib import Path
from typing import List, Tuple

try:
    import openai
except Exception:
    openai = None
try:
    from openai import OpenAI
except Exception:
    OpenAI = None
import time


def chunk_markdown(text: str, max_chars: int = 2000) -> List[str]:
    # Split on paragraphs first, then join until close to max_chars
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for p in paras:
        if cur and cur_len + len(p) + 2 > max_chars:
            chunks.append('\n\n'.join(cur))
            cur = [p]
            cur_len = len(p)
        else:
            cur.append(p)
            cur_len += len(p) + 2
    if cur:
        chunks.append('\n\n'.join(cur))
    # Further split any too-large single chunk
    out: List[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            out.append(c)
            continue
        # naive split by lines
        lines = c.split('\n')
        cur = []
        cur_len = 0
        for L in lines:
            if cur and cur_len + len(L) + 1 > max_chars:
                out.append('\n'.join(cur))
                cur = [L]
                cur_len = len(L)
            else:
                cur.append(L)
                cur_len += len(L) + 1
        if cur:
            out.append('\n'.join(cur))
    # final fallback: if any chunk is still too large (no newlines, long tokens), slice by character
    final: List[str] = []
    for c in out:
        if len(c) <= max_chars:
            final.append(c)
            continue
        # try to split on whitespace boundaries first
        start = 0
        L = len(c)
        while start < L:
            end = min(start + max_chars, L)
            # try to move end back to last space to avoid breaking words
            if end < L:
                last_space = c.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            final.append(c[start:end].strip())
            start = end
    return final


def cosine_similarity(a: List[float], b: List[float]) -> float:
    # pure-python cosine similarity
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def get_embeddings(texts: List[str], model: str = "text-embedding-3-small", batch_size: int = 128) -> List[List[float]]:
    if OpenAI is not None:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        embs: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = client.embeddings.create(model=model, input=batch)
            for item in resp.data:
                # item.embedding is a list of floats
                embs.append(item.embedding)
        return embs
    if openai is None:
        raise RuntimeError('openai package not available; install via requirements.txt')
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY environment variable not set')
    openai.api_key = api_key

    embs: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = openai.Embedding.create(model=model, input=batch)
        # response.data is a list of objects with 'embedding'
        for item in resp['data']:
            embs.append(item['embedding'])
    return embs


def call_chat_completion(messages, model: str = 'gpt-4o-mini', temperature: float = 0.0, retries: int = 3, backoff: float = 2.0):
    # Prefer new OpenAI client when available
    if OpenAI is not None:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        for attempt in range(1, retries + 1):
            try:
                resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature)
                # robust extraction from different response shapes
                try:
                    ch = resp.choices[0]
                    msg = getattr(ch, 'message', None) or (ch.get('message') if isinstance(ch, dict) else None)
                    if msg is not None:
                        cont = getattr(msg, 'content', None) or (msg.get('content') if isinstance(msg, dict) else None)
                        if isinstance(cont, list):
                            for item in cont:
                                if isinstance(item, dict) and 'text' in item:
                                    return item['text'].strip()
                                if isinstance(item, str):
                                    return item.strip()
                        if isinstance(cont, str):
                            return cont.strip()
                except Exception:
                    pass
                try:
                    out = getattr(resp, 'output', None) or (resp.get('output') if isinstance(resp, dict) else None)
                    if out:
                        for entry in out:
                            c = entry.get('content') if isinstance(entry, dict) else None
                            if isinstance(c, list):
                                for it in c:
                                    if isinstance(it, dict) and 'text' in it:
                                        return it['text'].strip()
                                    if isinstance(it, str):
                                        return it.strip()
                except Exception:
                    pass
                return str(resp)
            except Exception:
                if attempt == retries:
                    raise
                time.sleep(backoff ** attempt)
    # fallback to legacy openai package
    if openai is None:
        raise RuntimeError('openai Python package not available (install via requirements.txt)')
    for attempt in range(1, retries + 1):
        try:
            resp = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature)
            return resp.choices[0].message.content.strip()
        except Exception:
            if attempt == retries:
                raise
            time.sleep(backoff ** attempt)


def dedupe_chunks(chunks: List[str], embeddings: List[List[float]], threshold: float = 0.90) -> List[Tuple[int, str]]:
    kept: List[Tuple[int, str]] = []  # (orig_index, text)
    kept_embs: List[List[float]] = []
    for idx, (c, e) in enumerate(zip(chunks, embeddings)):
        is_dup = False
        for ke in kept_embs:
            sim = cosine_similarity(e, ke)
            if sim >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append((idx, c))
            kept_embs.append(e)
    return kept


def load_prompt(value: str) -> str:
    # If value is a path to a file, read it; otherwise return the raw string
    if not value:
        return ''
    p = Path(value)
    if p.exists() and p.is_file():
        return p.read_text(encoding='utf-8')
    return value


def rewrite_chunks(chunks: List[str], system_prompt: str, user_prompt: str, model: str, temperature: float, retries: int = 2) -> List[str]:
    out: List[str] = []
    sys_msg = system_prompt or (
        """
        # Role
        당신은 대한민국 '부동산 거래 및 법률 분석 전문가'이자 '데이터 정제용 AI'입니다. 
        사용자는 웹 크롤링을 통해 수집된, 노이즈(잡담, 광고 등)가 섞인 비정형 부동산 텍스트 데이터를 제공할 것입니다.
        당신의 임무는 이 데이터에서 '실무적인 부동산 거래와 계약'에 필요한 핵심 정보만을 추출하여 구조화된 보고서로 변환하는 것입니다.

        # Exclusion Rules (반드시 제거해야 할 내용)
        1. 부동산 매물 홍보성 멘트 (예: '초역세권', '대박 기회', '최고의 뷰' 등 감정적 수식어)
        2. 중개사무소 홍보, 전화번호, 블로그 이웃 추가 요청, 인사말 등
        3. 부동산 거래와 직접 관련 없는 지역 맛집, 날씨, 개인적인 일상 이야기
        4. 중복되거나 의미 없는 특수문자 및 반복 문구

        # Extraction Criteria (반드시 포함해야 할 내용)
        데이터에 다음 내용이 포함되어 있다면 우선적으로 추출하고 정리하십시오.
        1. **거래 조건**: 매매가, 전/월세 보증금, 융자금, 계약금/잔금 비율 및 일정
        2. **계약 필수 정보**: 등기부등본 확인 사항(근저당, 가압류 등), 건축물대장 정보(불법건축물 여부)
        3. **특약 사항**: 계약서에 명시해야 할 주의 조항 (예: 누수 책임, 원상복구, 반려동물 특약 등)
        4. **절차 및 서류**: 계약 시 필요 서류, 확정일자/전입신고 유의사항, 세금 관련 내용

        # Output Format (마크다운)
        결과는 반드시 아래 양식에 맞춰 출력하십시오. 해당 내용이 원문에 없으면 '정보 없음'으로 표기하지 말고 해당 항목을 생략하십시오.

        ## 1. 거래 및 계약 핵심 요약
        - **거래 유형**: 
        - **주요 금액 정보**: 

        ## 2. 권리 분석 및 법적 유의사항
        - (등기부등본, 권리관계 등 법적 리스크 관련 내용 요약)

        ## 3. 계약서 특약 추천 및 주의점
        - (실제 계약서 작성 시 넣어야 할 구체적인 문구 또는 조건)

        ## 4. 필요 서류 및 행정 절차
        - (단계별 준비물 및 신고 절차)
        """
    )
    user_pref = user_prompt or "웹에서 수집한 부동산 관련 텍스트입니다. 설정된 시스템 프롬프트의 규칙(노이즈 제거, 핵심 추출, 포맷 준수)에 따라 정리해 주세요."

    for i, c in enumerate(chunks):
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": f"{user_pref}\n\nSOURCE:\n{c}"},
        ]
        try:
            out_text = call_chat_completion(messages, model=model, temperature=temperature, retries=retries)
        except Exception as e:
            # On failure, fall back to original chunk to avoid data loss
            out_text = c
        out.append(out_text)
    return out


def process_file(path: Path, args) -> Path:
    text = path.read_text(encoding='utf-8')
    chunks = chunk_markdown(text, max_chars=args.chunk_chars)
    print(f'File {path.name}: split into {len(chunks)} chunks')
    embeddings = get_embeddings(chunks, model=args.emb_model, batch_size=args.batch_size)
    kept = dedupe_chunks(chunks, embeddings, threshold=args.threshold)
    print(f'Kept {len(kept)} / {len(chunks)} chunks after deduplication (threshold={args.threshold})')
    out_path = Path(args.output_dir) / (path.stem + '_dedup.md')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # preserve original order by orig index
    kept_sorted = sorted(kept, key=lambda t: t[0])
    # optionally rewrite kept chunks using chat model and provided prompts
    if args.rewrite:
        sys_prompt = load_prompt(args.system_prompt)
        user_prompt = load_prompt(args.user_prompt)
        to_rewrite = [txt for _, txt in kept_sorted]
        print(f'Rewriting {len(to_rewrite)} chunks with model={args.rewrite_model}...')
        rewritten = rewrite_chunks(to_rewrite, sys_prompt, user_prompt, model=args.rewrite_model, temperature=args.rewrite_temperature)
        final_chunks = rewritten
    else:
        final_chunks = [txt for _, txt in kept_sorted]

    with out_path.open('w', encoding='utf-8') as fh:
        for i, txt in enumerate(final_chunks):
            fh.write(txt)
            if i < len(final_chunks) - 1:
                fh.write('\n\n---\n\n')
    return out_path


def main():
    p = argparse.ArgumentParser(description='Semantic dedupe of markdown files using OpenAI embeddings')
    p.add_argument('inputs', nargs='+', help='Input markdown files')
    p.add_argument('--merge', action='store_true', help='Merge inputs and dedupe across them')
    p.add_argument('--output-dir', default='cleaned', help='Directory for cleaned outputs')
    p.add_argument('--chunk-chars', type=int, default=3000, help='Approx max chars per chunk')
    p.add_argument('--emb-model', default='text-embedding-3-small', help='Embedding model')
    p.add_argument('--batch-size', type=int, default=128, help='Batch size for embedding requests')
    p.add_argument('--threshold', type=float, default=0.96, help='Cosine similarity threshold to treat as duplicate (0-1)')
    # rewriting options
    p.add_argument('--rewrite', action='store_true', help='Run a rewrite pass using a chat model to normalize chunks')
    p.add_argument('--system-prompt', default='', help='System prompt text or path to file')
    p.add_argument('--user-prompt', default='', help='User prompt text or path to file (the chunk will be appended as SOURCE)')
    p.add_argument('--rewrite-model', default='gpt-4o-mini', help='Chat model to use for rewriting')
    p.add_argument('--rewrite-temperature', type=float, default=0.0, help='Temperature for rewrite chat model')
    args = p.parse_args()

    inputs = [Path(p) for p in args.inputs]
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # ensure OPENAI_API_KEY is set for both embeddings and chat
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print('ERROR: OPENAI_API_KEY environment variable not set')
        raise SystemExit(2)
    if openai is None:
        print('ERROR: openai package not installed. Run: pip install -r requirements.txt')
        raise SystemExit(2)
    openai.api_key = api_key

    if args.merge:
        all_chunks: List[str] = []
        for pth in inputs:
            txt = pth.read_text(encoding='utf-8')
            all_chunks.extend(chunk_markdown(txt, max_chars=args.chunk_chars))
        print(f'Merged inputs into {len(all_chunks)} chunks')
        embeddings = get_embeddings(all_chunks, model=args.emb_model, batch_size=args.batch_size)
        kept = dedupe_chunks(all_chunks, embeddings, threshold=args.threshold)
        kept_sorted = sorted(kept, key=lambda t: t[0])
        out_path = Path(args.output_dir) / 'merged_dedup.md'
        with out_path.open('w', encoding='utf-8') as fh:
            for i, (_, txt) in enumerate(kept_sorted):
                fh.write(txt)
                if i < len(kept_sorted) - 1:
                    fh.write('\n\n---\n\n')
        print(f'WROTE {out_path}')
    else:
        for pth in inputs:
            out = process_file(pth, args)
            print(f'WROTE {out}')


if __name__ == '__main__':
    main()
