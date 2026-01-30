import os
import random
import argparse
from datetime import datetime
from docxtpl import DocxTemplate
from langchain_openai import ChatOpenAI  # langchain-openai 패키지 필요
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
import json

# 1. Pydantic 모델 정의 (기존과 동일)
class Contract(BaseModel):
    # [메타데이터 필드 추가] - DOCX 렌더링에는 쓰이지 않지만 JSON 저장용으로 사용
    is_anomaly_data: bool = Field(False, description="이 데이터가 비정상(Anomaly) 데이터인지 여부")
    anomaly_category: Optional[str] = Field(None, description="비정상 유형 카테고리 (예: 날짜 오류, 금액 오류, 독소 조항 등)")
    anomaly_description: Optional[str] = Field(None, description="구체적으로 어떤 부분이 비정상인지에 대한 상세 설명")

    # --- 1. 계약 당사자 (서두) ---
    lessor: str = Field(..., description="임대인 성명 (서두)")
    lessee: str = Field(..., description="임차인 성명 (서두)")

    # --- 2. 부동산의 표시 ---
    property_address: str = Field(..., description="소재지 (주소)")
    land_category: str = Field(..., description="토지 지목")
    land_area: str = Field(..., description="토지 면적 (㎡)") 
    building_structure_usage: str = Field(..., description="건물 구조 및 용도")
    building_total_area: str = Field(..., description="건물 전체 면적 (㎡)")
    rental_portion: str = Field(..., description="임차할 부분 (예: 101동 2703호)")
    rental_portion_area: str = Field(..., description="임차할 부분 면적 (㎡)")

    # --- 3. 계약금 및 보증금 (제1조) ---
    deposit_str: str = Field(..., description="보증금 (한글 표기)")
    deposit_int: int = Field(..., description="보증금 (숫자 표기). 500만원 이상 1억원 이하 필수.", ge=5000000, le=100000000)
    down_payment_str: str = Field(..., description="계약금 (한글 표기)")
    down_payment_int: int = Field(..., description="계약금 (숫자 표기)")
    down_payment_receiver: str = Field(..., description="계약금 영수자 성명")
    
    # --- 4. 잔금 및 차임 (제1조 계속) ---
    balance_str: str = Field(..., description="잔금 (한글 표기)")
    balance_int: int = Field(..., description="잔금 (숫자 표기)")
    balance_payment_year: int = Field(..., description="잔금 지급 연도")
    balance_payment_month: int = Field(..., description="잔금 지급 월")
    balance_payment_day: int = Field(..., description="잔금 지급 일")
    
    monthly_rent_amount: int = Field(0, description="월세 (숫자 표기). 30만원 이상 100만원 이하 필수.", ge=300000, le=1000000)
    rent_payment_day: int = Field(..., description="월세 지급일 (매월 며칠)")
    
    maintenance_fee_str: Optional[str] = Field(None, description="관리비 (한글 표기/정액인 경우)")
    maintenance_fee_int: Optional[int] = Field(None, description="관리비 (숫자 표기). 5만원 이상 9만원 이하 필수.", ge=50000, le=90000)

    # --- 5. 임대차 기간 (제2조) ---
    lease_start_year: int = Field(..., description="임대차 시작 연도")
    lease_start_month: int = Field(..., description="임대차 시작 월")
    lease_start_day: int = Field(..., description="임대차 시작 일")
    lease_end_year: int = Field(..., description="임대차 종료 연도")
    lease_end_month: int = Field(..., description="임대차 종료 월")
    lease_end_day: int = Field(..., description="임대차 종료 일")

    # --- 6. 수리 및 시설 (제3조, 제4조) ---
    repair_details: Optional[str] = Field("없음", description="수리가 필요한 시설 내용")
    repair_completion_year: Optional[int] = Field(None, description="수리 완료 약정 연도")
    repair_completion_month: Optional[int] = Field(None, description="수리 완료 약정 월")
    repair_completion_day: Optional[int] = Field(None, description="수리 완료 약정 일")
    
    lessor_repair_responsibility: Optional[str] = Field("보일러 등 주요 설비 노후로 인한 고장", description="임대인 수선 부담 내용")
    lessee_repair_responsibility: Optional[str] = Field("임차인의 고의 및 과실로 인한 파손, 전구 등 소모품", description="임차인 수선 부담 내용")

    # --- 7. 중개보수 (제12조) ---
    brokerage_fee_rate: float = Field(..., description="중개보수 요율 (%). 0.3% ~ 0.9% 사이.", ge=0.3, le=0.9)
    brokerage_fee_total: int = Field(..., description="중개보수 총액")

    # --- 8. 확인설명서 교부일 (제13조) ---
    doc_delivery_year: int = Field(..., description="확인·설명서 교부 연도")
    doc_delivery_month: int = Field(..., description="확인·설명서 교부 월")
    doc_delivery_day: int = Field(..., description="확인·설명서 교부 일")

    # --- 9. 특약사항 ---
    special_term_1: Optional[str] = Field(None, description="특약사항 1")
    special_term_2: Optional[str] = Field(None, description="특약사항 2")
    special_term_3: Optional[str] = Field(None, description="특약사항 3")
    special_term_4: Optional[str] = Field(None, description="특약사항 4")
    special_term_5: Optional[str] = Field(None, description="특약사항 5")

    # --- 10. 인적사항 상세 (임대인) ---
    lessor_address: str = Field(..., description="임대인 주소")
    lessor_registration_number: str = Field(..., description="임대인 주민등록번호")
    lessor_phone: str = Field(..., description="임대인 전화번호")
    lessor_name: str = Field(..., description="임대인 성명 (서명란)")
    
    lessor_rep_address: Optional[str] = Field("", description="임대인 대리인 주소")
    lessor_rep_registration_number: Optional[str] = Field("", description="임대인 대리인 주민등록번호")
    lessor_rep_name: Optional[str] = Field("", description="임대인 대리인 성명")

    # --- 11. 인적사항 상세 (임차인) ---
    lessee_address: str = Field(..., description="임차인 주소")
    lessee_registration_number: str = Field(..., description="임차인 주민등록번호")
    lessee_phone: str = Field(..., description="임차인 전화번호")
    lessee_name: str = Field(..., description="임차인 성명 (서명란)")
    
    lessee_rep_address: Optional[str] = Field("", description="임차인 대리인 주소")
    lessee_rep_registration_number: Optional[str] = Field("", description="임차인 대리인 주민등록번호")
    lessee_rep_name: Optional[str] = Field("", description="임차인 대리인 성명")

    # --- 12. 개업공인중개사 정보 ---
    broker_office_address: str = Field(..., description="중개사 사무소 소재지")
    broker_office_name: str = Field(..., description="중개사 사무소 명칭")
    broker_rep_name: str = Field(..., description="공인중개사 대표 성명")
    broker_registration_number: str = Field(..., description="중개사 등록번호")
    broker_phone: str = Field(..., description="중개사 사무소 전화번호")


def generate_contract_data(is_anomaly=False):
    """
    계약서에 들어갈 데이터를 생성하는 함수
    is_anomaly=True일 경우, 고의로 오류 데이터를 생성함
    """

    system_prompt = """
    You are an AI agent generating synthetic data for the South Korean 'Standard Residential Lease Agreement' (주택임대차표준계약서). 
    Strictly adhere to the following rules when generating data.
    
    1. **Location**: Use realistic 'Road Name Addresses' located in Seoul, Gyeonggi, Incheon, Busan, or Daegu.
    2. **Amounts**: 
       - deposit_int: Between 5 million KRW and 100 million KRW.
       - monthly_rent_amount: Between 300,000 KRW and 1 million KRW.
       - maintenance_fee_int: Between 50,000 KRW and 90,000 KRW.
       - All amounts are based on Korean Won (KRW) and must be generated realistically according to market rates.
       - **Korean Text Representation**: Write all amounts in pure Korean characters only, omitting the word "원" at the end. (e.g., write "팔십만" instead of "팔십만원").
       - **Numeric Representation**: Do not abbreviate numbers; strictly use commas for formatting. (e.g., 800,000).
    3. **Dates**: 
       - Contract Date: Between the years 2024 and 2026.
       - Balance Date: 1 to 2 months after the Contract Date.
       - Lease Term: Defaults to 24 months (2 years) starting from the Balance Date; ensure the end date is calculated correctly (one day prior to the full 2-year mark).
    4. **Names**: Use common 3-syllable Korean names.
    5. Replace any "None" values with a single space " ".
    6. Provide exactly 5 special terms (riders).
    7. You must explicitly specify 'Content of Repairs' (수리할 내용) and 'Completion Timing of Repairs' (수리 완료 시기).
    8. Draft the special terms by referring to the following examples:
        "
        1. 본 계약은 임차인의 전세자금 대출 실행을 전제로 하며, 임대인 또는 임차목적물의 하자로 인한 전세자금대출 미승인 시 계약은 무효로 하고 임대인은 계약금을 즉시 반환한다.
        2. 임대인은 임차인의 전세보증금 반환보증 보험 가입을 위해 필요한 절차에 적극 협조한다. 단, 잔금 지급 후 1~2개월 내에 임대인 또는 임차목적물의 하자로 인해 보증보험 가입이 거절될 경우 계약은 무효로 하며, 임대인은 수령한 계약금, 중도금, 잔금 전액을 즉시 반환한다.
        3. 임대인은 계약일로부터 잔금 및 입주일자 익일(다음날)까지 현재 상태의 등기부등본을 유지해야 하며, 담보권(근저당)이나 전세권 설정 등 새로운 권리를 발생시키지 않는다. (위반 시 계약 해지 및 손해배상)
        4. 임대인은 국세나 지방세, 근저당권의 이자 체납이 없음을 고지하며, 임차인이 세금 체납 내역을 확인하는 것에 적극 협조한다. 만일 잔금일 전까지 세금 체납이 확인될 경우 임대인은 이를 전액 상환해야 하며, 불이행 시 계약은 무효로 하고 계약금을 즉시 반환한다.
        5. 임대인은 잔금 지급일 또는 보증보험 가입 예정일 당일까지 매매 등 소유권 이전 등기를 신청하지 않는다.
        6. 임대기간 중 주택의 매매계약을 체결하거나 소유권을 이전할 경우 사전에 임차인에게 고지해야 한다. 만약 양수인(새 집주인)의 사유로 전세보증보험 가입/유지가 어려워 임대차 승계가 불가능할 경우, 임차인은 계약을 해지하고 기존 임대인에게 보증금 반환을 청구할 수 있다.
        7. 임대차 계약 만료 시, 임대인은 타 임차인의 임대 여부(다음 세입자를 구하는 것)와 관계없이 보증금을 만료일에 즉시 반환한다.
        8. (근저당이 있는 경우) 현재 등기부등본상 설정된 1순위 근저당권(OO은행, 채권최고액 OOO원)은 잔금일에 전액 상환 및 말소하기로 한다.
        9. 애완동물(개, 고양이 등 모든 반려동물) 반입 및 실내 흡연을 금지한다. 위반 시 임대인은 임대차계약을 해지할 수 있으며, 이에 따른 손해배상(도배, 탈취 비용 등)을 청구할 수 있다.
        10. 임차인의 고의 또는 부주의로 인한 시설물 훼손 시 원상복구하기로 한다. 단, 통상적인 사용에 의한 자연적인 마모나 변색은 복구 의무에서 제외한다.
        11. 임대차 기간 중 임차인이 대납한 장기수선충당금은 계약 만료 및 퇴거 시 임대인이 임차인에게 전액 반환한다.
        12. 난방, 상하수도, 전기 시설 등 주요 설비의 노후로 인한 고장은 임대인이 수리하며, 임차인의 부주의로 인한 파손 및 전구 등 소모품 교체는 임차인이 부담한다.
        13. 묵시적 갱신된 경우, 임차인은 언제든지 계약 해지를 통지할 수 있으며 임대인이 통지를 받은 날부터 3개월이 지나면 해지의 효력이 발생한다. 이때 중개보수는 임대인이 부담한다.
        "
        
    [IMPORTANT: Metadata Creation]
    You must populate the `is_anomaly_data`, `anomaly_category`, and `anomaly_description` fields for the generated data.
    - For Normal Data: Set `is_anomaly_data=False`, `anomaly_category="Normal"`, and `anomaly_description="정상 데이터"`.
    - For Anomalous Data: Set `is_anomaly_data=True`, `anomaly_category="Error Type (e.g., Date Inversion)"`, and provide a specific description in `anomaly_description` (e.g., "Balance date is earlier than contract date").
    """

    # 3. User Input: 정상 vs 비정상 시나리오 분기
    if is_anomaly:
        user_input = """
        [INSTRUCTIONS]
        This time, generate **anomalous data containing 'sophisticated errors even experts might miss' or 'toxic clauses fatal to tenants'.**
        Follow the normal rules for the rest of the data, but **randomly select and apply ONLY ONE of the following 11 scenarios.**

        [Error and Toxic Clause Scenarios]
        
        1. **[Summation Error]**: 
           - Record the Security Deposit and Down Payment correctly, but write the **Balance** as the value of `(Security Deposit - Down Payment)` with **1,000,000 KRW added or subtracted**.

        2. **[Date Inversion Error]**:
           - Set the **Balance Payment Date (Move-in Date)** to a date 1~3 days prior to the contract date (past), or to the exact same date as the contract date.

        3. **[Lease Term Calculation Error]**:
           - Set the lease expiration date to exactly 2 years after the start date. 
           - (Error Example: 2024-01-01 ~ 2026-01-01 / Normal should be 2025-12-31)

        4. **[Resident Registration Number Rule Violation]**:
           - Set the first digit of the lessor's resident registration number (back section) to one of **5, 6, 7, 8 (Foreigner Code)**, but write the name as a common Korean name.

        5. **[Excessive Brokerage Fee]**:
           - brokerage_fee_rate: Between 0.5% and 0.9%.
        
        6. **[Amount Text-Number Mismatch]**:
           - Write the correct amount in Korean text for the deposit or monthly rent, but write a value with **one '0' added or removed** in the parentheses for Arabic numerals.
           - (Error Example: 금 일억 원정 (₩10,000,000))

        7. **[Exclusive Area Conversion Error]**:
           - Record the exclusive area ($m^2$) correctly, but write a value in the Pyeong conversion field that is **completely different (±5 Pyeong or more difference)** from the `$m^2 \times 0.3025$` calculation. (Error Example: 59$m^2$ (approx. 32 Pyeong) -> Actually approx. 18 Pyeong)

        8. **[Account Holder Mismatch]**:
           - Set the lessor's name and the **account holder name** for the deposit/rent account to be different people (third party).
           - (Purpose: Simulate signs of charter fraud or missing power of attorney in agent contracts).

        9. **[Address Unit Number Error]**:
           - Write the correct unit number (e.g., Unit 301) in the 'Location' field at the top, but mix in a **similar but different unit number (e.g., Unit 302, B01)** in the special terms or confirmation section.

        10. **[Contact Number Format/Duplication Error]**:
           - Write the lessor's and lessee's contact numbers (mobile) as the **exact same number**, or set them to a **number with incorrect digits** (e.g., 010-123-4567, 7 digits) lacking a valid format.

        11. **[Inclusion of Ambiguous Toxic Clauses]**:
           - Calculate all dates and amounts perfectly, but insert 1~2 lines of **Special Terms** that are unilaterally disadvantageous to the tenant or legally void.
           - Pick one from the list below:
           - (Content: "관리비 및 공과금은 임대인이 정하는 바에 따른다.", Reason: 사용 내역 미공개 및 임대인의 자의적인 금액 인상을 방지하기 위해 정액제 또는 증빙 협의로 수정 필요)
           - (Content: "퇴거 시 청소비는 실비로 정산한다.", Reason: 과도한 청소비 청구를 막기 위해 확정된 금액을 명시해야 함)
           - (Content: "계약 만료 전 퇴거 시, 남은 기간의 월세를 위약금으로 지불한다.", Reason: 세입자가 다음 임차인을 구할 경우 중개보수와 단기 공실 비용만 부담하는 것이 공정함)
           - (Content: "애완동물 사육 시 도배·장판 비용 전액을 배상한다.", Reason: 훼손 범위와 상관없는 전체 교체 비용 청구는 과도하므로 실제 훼손 부분에 한정해야 함)
           - (Content: "계약 갱신 시 중개보수는 임차인이 부담한다.", Reason: 재계약이나 묵시적 갱신은 원칙적으로 중개보수 의무가 없으므로 삭제가 타당함)
           - (Content: "부가세 별도 (상가 겸용 주택 등)", Reason: 실제 지불 금액에 대한 오해를 방지하기 위해 부가세 포함 여부를 명확히 확정해야 함)
           - (Content: "배관 막힘 비용은 원인 불문 임차인이 부담한다.", Reason: 노후나 구조적 결함으로 인한 막힘까지 임차인에게 전가하는 것은 부당하므로 과실 여부를 따져야 함)
           - (Content: "결로 및 곰팡이는 임차인의 환기 소홀로 간주한다.", Reason: 건물 단열 등 구조적 하자로 인한 경우 임대인 책임임을 명시하여 책임을 분명히 함)
           - (Content: "옵션 품목의 수리 및 교체는 임차인이 한다.", Reason: 기본 옵션의 노후 고장은 임대인의 수선 의무에 해당하므로 고의·과실이 없을 시 임대인이 부담해야 함)
           - (Content: "동파 사고 시 수리비는 전액 임차인이 부담한다.", Reason: 임차인이 방지 조치를 다 했음에도 발생한 구조적 동파는 임대인 책임임)
           - (Content: "방충망, 도어락 배터리 등 소모품 일체는 임차인 부담.", Reason: 입주 시점부터 파손된 항목은 임대인이 수리해 주는 것이 원칙임)
           - (Content: "임대인은 시설 점검을 위해 언제든 출입할 수 있다.", Reason: 주거권 침해 및 주거침입 소지가 크므로 사전 동의 절차를 반드시 넣어야 함)
           - (Content: "실내 흡연, 못 박기 등 적발 시 즉시 계약을 해지한다.", Reason: 단순 생활 습관이나 경미한 행위로 즉시 퇴거를 요구하는 것은 과도하므로 원상복구 비용 청구로 대체해야 함)
           - (Content: "지인 및 친척의 숙박을 금지한다.", Reason: 일시적 방문까지 제한하는 것은 사생활에 대한 지나친 간섭이므로 삭제가 필요함)
           - (Content: "임대차 등기 설정을 금지한다.", Reason: 법적 권리인 임차권등기명령 등을 방해할 목적의 특약은 분쟁의 씨앗이 되므로 삭제 권장)
           - (Content: "못 자국, 벽지 변색 등 일체를 원상복구한다.", Reason: 시간 경과에 따른 자연스러운 생활 마모(통상적 가치 감소)는 임차인의 의무가 아님)
           - (Content: "퇴거 시 신규 세입자의 취향에 맞춰 도배를 해준다.", Reason: 임차인의 과실과 무관한 제3자의 취향까지 비용을 부담할 이유가 전혀 없음)
           - (Content: "만기 통보는 1개월 전까지 없으면 자동 연장된 것으로 본다.", Reason: 현행 주택임대차보호법상 2개월 전임을 인지하지 못해 발생하는 불이익을 방지해야 함)
           - (Content: "보증금 반환은 공과금 정산이 완료된 후 실시한다.", Reason: 정산 핑계로 보증금 반환이 지연되는 것을 막기 위해 선 반환 후 정산 방식을 택해야 함)
           - (Content: "본 특약은 법정 규정보다 우선한다.", Reason: 주택임대차보호법은 강행규정으로 임차인에게 불리한 특약은 효력이 없음을 유의해야 함)

        Generate data containing **EXACTLY ONE** of the 11 scenarios listed above.
        """
        
    else:
        user_input = """
        [Essential Knowledge & Rules for Data Generation]
        Strictly apply the following calculation formulas and conventions to generate the data.

        1. **Money Logic (Consistency of Amounts)**:
           - **[Deposit Structure]**: `Total Security Deposit = Down Payment + Balance` (Assume no interim payments).
           - **[Down Payment Ratio]**: Set the Down Payment to **5% or 10%** of the Total Security Deposit. (e.g., If the Deposit is 100 million KRW, the Down Payment is 5 million or 10 million KRW).
           - **[Balance]**: Calculate exactly as `Total Security Deposit - Down Payment`.
           - **[Units]**: Set all amounts to be exactly divisible by 1,000,000 KRW (flat million units).

        2. **Brokerage Fee Logic (Calculation Formula)**:
           - Brokerage fees must be calculated based on the **'Converted Deposit Amount'**.
           - **[Converted Deposit Formula]**:
             * For Jeonse (Charter): `Converted Deposit = Security Deposit`
             * For Monthly Rent: `Converted Deposit = Security Deposit + (Monthly Rent Amount * 100)`
           - **[Rate Application]**: 
             * Converted Deposit under 50 million KRW: 0.5% (Max Limit: 200,000 KRW)
             * Converted Deposit 50 million ~ under 200 million KRW: 0.4% (Max Limit: 300,000 KRW) -> **Prioritize generating data in this range.**
             * Converted Deposit 200 million ~ under 900 million KRW: 0.3%
           - **[Total Brokerage Fee]**: `Converted Deposit * Rate` (However, if a maximum limit exists, determine the fee within that limit).
           - Since VAT is separate, either add 10% to the calculated amount or assume 'VAT excluded' and write the base amount only.

        3. **Date Logic (Logical Order)**:
           - **[Contract Date]**: A weekday between January 2024 and December 2025.
           - **[Balance Date (Move-in Date)]**: A weekday or Saturday approximately **3 to 8 weeks (1~2 months)** after the Contract Date. (Exclude Sundays).
           - **[Lease Term]**: Set exactly to **24 months (2 years)** from the Balance Date, but set the End Date to the day before the Start Date.
             * (e.g., Start Date: 2024-03-02 -> End Date: 2026-03-01)
           - **[Confirmation Statement Date]**: Must be set to the **same date as the Contract Date**.
           - **[Repair Completion Date]**: Set to the same date as the Lease Start Date.

        4. **Maintenance & Repair Obligations**:
           - Randomly combine the following repair obligations for the lessor and lessee.
           - **[Lessor's Liability (Aging & Structural Defects)]**:
             * Heating & Water Supply: Boiler body/controller malfunction, water pipe leaks or freezing (structural causes).
             * Electrical & Options: Malfunction of built-in appliances (washing machine, fridge, AC) due to aging, ceiling recessed lights (LED module) failure.
             * Building Structure: Ceiling/wall leaks, rainwater inflow through window frames, glass breakage due to natural disasters like typhoons.
           - **[Lessee's Liability (Consumables & Negligence)]**:
             * Consumables Replacement: Fluorescent lights/bulb replacement, batteries for door locks/remotes, shower heads and hoses, faucet washers, damaged insect screens.
             * Negligence & Carelessness: Toilet/drain clogging due to foreign objects, condensation/mold due to lack of ventilation, wallpaper staining due to indoor smoking, door frame/floor damage caused by pets.

        5. **Resident Registration Number**: Must generate in the format where the first digit of the back section is one of **1, 2, 3, 4** (e.g., 990101-1234567).

        6. **brokerage_fee_rate**: Between 0.3% and 0.4%.

        Based on the rules above, generate flawless and perfect JSON data.
        """

    messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

    # 4. LLM 초기화 (gpt-4o 사용 추천)
    # 주의: 실행 환경에 OPENAI_API_KEY 환경변수가 설정되어 있어야 합니다.
    llm = ChatOpenAI(model="gpt-5.2", temperature=0.3) 
    structured_llm = llm.with_structured_output(Contract)
    final_contract = structured_llm.invoke(messages)
    return final_contract

import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # pip install python-dateutil 필요

def postprocess(contract_dict: dict) -> dict:
    """
    Contract 딕셔너리를 받아서, 숫자(int)로 된 금액 필드들을 
    천 단위 콤마가 찍힌 문자열(str)로 변환하여 반환합니다.
    (예: 1000000 -> "1,000,000")
    """

    
    contract_dict['brokerage_fee_total'] = int((contract_dict['deposit_int'] + 100*contract_dict['monthly_rent_amount'])*contract_dict['brokerage_fee_rate']*0.01)

    # 콤마를 찍고 싶은 필드 명단
    target_fields = [
        "deposit_int",          # 보증금
        "down_payment_int",     # 계약금
        "balance_int",          # 잔금
        "monthly_rent_amount",  # 월세
        "maintenance_fee_int",  # 관리비
        "brokerage_fee_total"   # 중개보수 총액
    ]

    for key in target_fields:
        # 해당 키가 있고, 값이 None이 아닐 때만 변환
        if key in contract_dict and contract_dict[key] is not None:
            # f-string의 :, 옵션을 사용하면 자동으로 천 단위 콤마 생성
            contract_dict[key] = f"{contract_dict[key]:,}"


    return contract_dict

def validate_contract_logic(contract) -> list:
    """
    Contract 객체(Pydantic)를 받아서 논리적 오류가 있는지 검사합니다.
    오류가 없으면 빈 리스트 []를 반환하고, 오류가 있으면 에러 메시지 리스트를 반환합니다.
    """
    errors = []

    # --- 1. 금액 정합성 검사 (Money Logic) ---
    # 규칙: 보증금 = 계약금 + 잔금
    if contract.deposit_int != (contract.down_payment_int + contract.balance_int):
        errors.append(
            f"[금액 오류] 보증금({contract.deposit_int}) != 계약금({contract.down_payment_int}) + 잔금({contract.balance_int})"
        )
    # --- 2. 중개보수 검사 (Money Logic) ---
    # 규칙: 중개보수 금액 = (보증금 + 100*월세)*중개보수 요율
    # if contract.brokerage_fee_total != (contract.deposit_int + 100*contract.monthly_rent_amount)*contract.brokerage_fee_rate:
    #     errors.append(
    #         f"[금액 오류] 중개보수 금액({contract.brokerage_fee_total}) != (보증금({contract.deposit_int}) + 100*월세({contract.monthly_rent_amount})) * 중개보수 요율({contract.brokerage_fee_rate})"
    #     )

    # 규칙: 모든 금액은 양수여야 함
    if contract.deposit_int < 0 or contract.monthly_rent_amount < 0:
        errors.append("[금액 오류] 보증금이나 월세가 음수입니다.")

    # 1. 보증금 범위: 5백만원 ~ 1억원
    if not (5000000 <= contract.deposit_int <= 100000000):
        errors.append(f"[범위 오류] 보증금({contract.deposit_int:,})이 허용 범위(500만~1억)를 벗어났습니다.")

    # 2. 월세 범위: 30만원 ~ 100만원
    if not (300000 <= contract.monthly_rent_amount <= 1000000):
        errors.append(f"[범위 오류] 월세({contract.monthly_rent_amount:,})가 허용 범위(30만~100만)를 벗어났습니다.")

    # 3. 관리비 범위: 5만원 ~ 9만원 (None이 아닐 경우에만 체크)
    if contract.maintenance_fee_int is not None:
        if not (50000 <= contract.maintenance_fee_int <= 90000):
            errors.append(f"[범위 오류] 관리비({contract.maintenance_fee_int:,})가 허용 범위(5만~9만)를 벗어났습니다.")

    # 4. 중개보수 요율 범위: 0.3% ~ 0.9%
    # (주의: float 비교이므로 약간의 오차를 고려하거나 부등호를 사용)
    if not (0.3 <= contract.brokerage_fee_rate <= 0.9):
        errors.append(f"[범위 오류] 중개보수 요율({contract.brokerage_fee_rate}%)이 허용 범위(0.3~0.9%)를 벗어났습니다.")

    # --- 2. 날짜 논리 검사 (Date Logic) ---
    try:
        # 날짜 객체 생성 (확인설명서 교부일은 계약일과 같다고 가정하여 비교용으로 사용 가능)
        contract_date = datetime(contract.doc_delivery_year, contract.doc_delivery_month, contract.doc_delivery_day)
        balance_date = datetime(contract.balance_payment_year, contract.balance_payment_month, contract.balance_payment_day)
        lease_start = datetime(contract.lease_start_year, contract.lease_start_month, contract.lease_start_day)
        lease_end = datetime(contract.lease_end_year, contract.lease_end_month, contract.lease_end_day)

        # 2-1. 계약일 vs 잔금일 (계약일은 잔금일보다 같거나 빨라야 함)
        if contract_date > balance_date:
            errors.append(f"[날짜 오류] 계약일({contract_date.date()})이 잔금일({balance_date.date()})보다 미래입니다.")

        # 2-2. 잔금일 == 임대차 시작일 (통상적으로 일치해야 함)
        if balance_date != lease_start:
            errors.append(f"[날짜 오류] 잔금일({balance_date.date()})과 임대차 시작일({lease_start.date()})이 다릅니다.")

        # 2-3. 임대차 기간 계산 (정확히 24개월인지 확인)
        # 규칙: 종료일 = 시작일 + 2년 - 1일 (예: 2024.01.01 ~ 2025.12.31)
        expected_end_date = lease_start + relativedelta(years=2) - timedelta(days=1)
        
        # 하루 이틀 차이는 허용할지, 엄격하게 할지 결정 (여기선 엄격하게 검사)
        if lease_end != expected_end_date:
            errors.append(
                f"[기간 오류] 종료일({lease_end.date()})이 2년 계약 규칙({expected_end_date.date()})과 맞지 않습니다."
            )
            
    except ValueError as e:
        errors.append(f"[날짜 형식 오류] 존재하지 않는 날짜가 포함되어 있습니다. (예: 2월 30일) - {e}")

    # --- 3. 포맷 정규식 검사 (Regex Validation) ---
    
    # 주민등록번호 형식 (6자리-7자리)
    jumin_pattern = re.compile(r"\d{6}-?[1-4]\d{6}")
    if not jumin_pattern.match(contract.lessor_registration_number):
        errors.append(f"[형식 오류] 임대인 주민번호 형식 위반: {contract.lessor_registration_number}")
    
    # 전화번호 형식 (010-XXXX-XXXX 또는 02-XXX-XXXX 등)
    phone_pattern = re.compile(r"^\d{2,3}-\d{3,4}-\d{4}$")
    if not phone_pattern.match(contract.lessor_phone):
        errors.append(f"[형식 오류] 임대인 전화번호 형식 위반: {contract.lessor_phone}")

    return errors

def create_dataset(template_path, output_dir, count=10):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for is_anomaly in [True, False]:
        for i in range(count):
            # 2. 데이터 생성
            contract_pydantic = generate_contract_data(is_anomaly)
            
            if contract_pydantic:
                # 3. 데이터 검증 (Python Rule-based)
                validation_errors = validate_contract_logic(contract_pydantic)
                
                # [로직 변경]
                # 정상(Normal) 데이터인데 에러가 있다? -> 저장 안 함 (재시도 필요하나 여기선 패스)
                # 비정상(Anomaly) 데이터인데 에러가 있다? -> 의도된 것이므로 저장 OK
                # 비정상(Anomaly - 독소조항)인데 에러가 없다? -> 의도된 것이므로 저장 OK
                
                should_save = False
                
                if not is_anomaly:
                    # 정상 데이터는 에러가 없어야 저장
                    if not validation_errors:
                        should_save = True
                    else:
                        print(f"⚠️ [Skip] Normal data has errors: {validation_errors}")
                else:
                    # 비정상 데이터는 무조건 저장 (단, 의도치 않은 에러일 수도 있으니 로그는 출력)
                    should_save = True
                    if validation_errors:
                        print(f"ℹ️ [Anomaly] Detected expected errors: {validation_errors}")

                if should_save:
                    # 4. [버그 수정] DocxTemplate은 반드시 루프 안에서 새로 로드해야 함
                    doc = DocxTemplate(template_path)
                    
                    context = contract_pydantic.model_dump()
                    postprocess(context)
                    doc.render(context)
                    
                    # 5. 파일명 설정
                    label = "abnormal" if contract_pydantic.is_anomaly_data else "normal"
                    base_filename = f"contract_{i+1}"
                    json_path = f"{output_dir}/{label}/{base_filename}.json"

                    # DOCX 저장
                    docx_path = f"{output_dir}/{label}/{base_filename}.docx"
                    doc.save(docx_path)
                    
                    # JSON에 저장할 메타데이터 구성
                    metadata = {
                        "filepath": docx_path,
                        "is_anomaly": contract_pydantic.is_anomaly_data,
                        "anomaly_category": contract_pydantic.anomaly_category,
                        "anomaly_description": contract_pydantic.anomaly_description,
                        "validation_errors_detected": validation_errors,
                    }
                        
                    print(f"✅ Generated: {docx_path} {json_path}")            
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=4)

# 실행
if __name__ == "__main__":
    load_dotenv()
    # API KEY 확인
    if "OPENAI_API_KEY" not in os.environ:
        print("Warning: OPENAI_API_KEY environment variable is not set.")

    args = argparse.ArgumentParser()
    # 경로 수정: 실제 파일이 있는 경로로 설정해주세요.
    args.add_argument("--template_path", type=str, default="./data/주택임대차표준계약서.docx")
    args.add_argument("--output_dir", type=str, default="./data")
    args.add_argument("--count", type=int, default=5) # 테스트를 위해 5개로 설정
    
    parsed_args = args.parse_args()

    create_dataset(parsed_args.template_path, parsed_args.output_dir, parsed_args.count)