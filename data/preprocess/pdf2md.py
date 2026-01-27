import time
from dotenv import load_dotenv
import os
import base64
import time
import io
from pdf2image import convert_from_path
from openai import OpenAI
import argparse
from tqdm import tqdm
load_dotenv()

os.getenv("OPENAI_API_KEY")
client = OpenAI()

def encode_image_to_base64(pil_image):
    buffered = io.BytesIO()
    pil_image.save(buffered, format="JPEG", quality=95)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def process_pdf_in_batches(pdf_path, batch_size=3):
    """
    PDF를 batch_size만큼 묶어서 GPT-4o에게 전송합니다.
    예: 64페이지 -> batch_size 페이지씩 묶어서 GPT-4o에게 전송합니다.
    """
    
    # 1. PDF -> 이미지 변환
    print("PDF를 이미지로 변환 중...")
    try:
        # thread_count를 늘리면 변환 속도가 빨라집니다
        all_pages = convert_from_path(pdf_path, dpi=300, thread_count=4)
    except Exception as e:
        print(f"PDF 변환 오류: {e}")
        return None

    total_pages = len(all_pages)
    full_markdown = ""
    
    print(f"총 {total_pages} 페이지. {batch_size}페이지씩 묶어서 처리합니다.")

    # 2. Batch 단위로 순회 (0~5, 5~10, ...)
    for start_idx in tqdm(range(0, total_pages, batch_size)):
        end_idx = min(start_idx + batch_size, total_pages)
        current_batch = all_pages[start_idx:end_idx]
        
        # print(f"Processing Batch: Page {start_idx+1} ~ {end_idx}...")

        # 3. 메시지 컨텐츠 구성 (텍스트 프롬프트 + 이미지 N개)
        user_content = [
            {
                "type": "text", 
                "text": f"""
                여기 제공된 이미지는 부동산 문서의 {start_idx+1}페이지부터 {end_idx}페이지입니다.
                이 이미지를 보고 **모든 텍스트와 표를 빠짐없이** Markdown 포맷으로 변환하세요.

                [강력한 제약 사항]
                1. **절대 요약 금지**: 토씨 하나도 빼먹지 말고 그대로 전사(Transcription)하세요.
                2. **표(Table) 처리 전략 (매우 중요)**: 
                    - 시각적인 Markdown 표(`|---|`) 문법 사용을 **지양**하세요. 표가 깨지거나 헤더와 내용이 분리될 수 있습니다.
                    - 대신, 표의 각 행(Row)을 **"항목명: 값"** 형태의 명확한 리스트나 서술형 문장으로 풀어서 작성하세요.
                    - *예시:* (나쁜 예) `| 1 | 소유권이전 | 2024.01.01 |`
                        (좋은 예) `- 순위번호 1번: 소유권이전 등기 (접수일: 2024년 1월 1일)`
                3. **할루시네이션 방지**: 
                   - 글자가 흐릿하거나 잘려서 보이지 않으면 추측해서 쓰지 말고 `(판독불가)`라고 적으세요.
                   - 없는 내용을 지어내지 마세요.
                4. **개인정보**: 주민등록번호 뒷자리는 `******`로 마스킹하세요.
                5. **출력 형식**: 서론(Introduction)이나 결론(Conclusion) 멘트를 달지 말고, 오직 Markdown 본문만 출력하세요.
                """
            }
        ]

        # 배치 내의 이미지들을 하나씩 인코딩해서 리스트에 추가
        for img in current_batch:
            base64_img = encode_image_to_base64(img)
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_img}",
                    "detail": "high"
                }
            })

        # 4. API 호출 (재시도 로직 포함 권장)
        try:
            response = client.chat.completions.create(
                model="gpt-4o", 
                temperature=0,
                messages=[
                    {
                        "role": "system", 
                        "content": """
                        당신은 세계 최고의 OCR(광학 문자 인식) AI입니다. 부동산 문서의 복잡한 레이아웃과 한국어 특약 사항을 완벽하게 인식하여 구조화된 Markdown으로 변환합니다.
                        """
                    },
                    {
                        "role": "user", 
                        "content": user_content
                    }
                ]
            )
            
            batch_result = response.choices[0].message.content
            full_markdown += f"\n\n\n{batch_result}"
            
            # Rate Limit 방지를 위한 짧은 휴식 (중요!)
            time.sleep(1) 

        except Exception as e:
            print(f"Error processing batch {start_idx+1}~{end_idx}: {e}")
            # 실무에서는 여기서 retry 로직을 추가하거나 로그를 남깁니다.
            
    return full_markdown


if __name__ == '__main__':
    argparse = argparse.ArgumentParser()
    argparse.add_argument("--pdf_path", type=str, required=True)
    argparse.add_argument("--batch_size", type=int, default=3)
    args = argparse.parse_args()

    result = process_pdf_in_batches(args.pdf_path, batch_size=args.batch_size)
    
    if result:
        file_name = args.pdf_path.split("/")[-1].replace(".pdf", ".md")
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(result)
        print("전체 변환 완료!")
    else:
        print("변환 실패")