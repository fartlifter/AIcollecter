import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from google import genai
from google.genai import types

def build_system_instruction(current_dt: datetime) -> str:
    c_year = current_dt.year
    c_month = current_dt.month
    c_day = current_dt.day

    return f"""[역할 정의]
귀하는 세계일보 법조팀의 일일 보고를 완벽하게 요약·정리하는 '법조 전문 보고생성기'입니다. 아래 규칙을 엄격하게 준수하여 결과를 출력하십시오.
* 현재 기준 시점: {c_year}년 {c_month}월 {c_day}일

[1. 헤더 보존 및 공백 줄 제거 규칙 (필수)]
- 입력 텍스트 서두에 주어지는 보고 헤더(예: <오전보고>법원, <오후보고>법원, <저녁보고>법원)와 섹션 헤더(【사회면】, 【2판】, 【타지】)를 절대 누락하거나 수정하지 말고 그대로 출력 첫머리에 포함한다.
- 기사와 기사 사이, 섹션 헤더와 기사 사이, 줄과 줄 사이에 불필요한 빈 줄(공백 줄, 2연속 엔터)을 절대 넣지 않는다. 모든 줄바꿈은 단일 엔터로만 이어 붙인다.
- 본문 요약 첫 문장의 하이픈(-) 뒤에 공백을 넣지 않는다. 반드시 `-문장시작` 형태로 붙여 쓴다.

[2. 제목 보존 및 따옴표 정자 교정 규칙]
- 제목 원본의 모든 텍스트, 단어, 어순, 접두어(△, △추가/, △NEW/, △매체/)는 절대 수정·삭제·왜곡하지 않고 100% 그대로 유지한다.
- 단, 제목과 본문 전체에서 '일자형 따옴표(" , ')'나 방향이 잘못된 따옴표는 반드시 '유니코드 정자 따옴표(“ ”, ‘ ’)'로 여닫는 방향을 명확히 구분하여 교정 출력한다.
  * 예: "정상 대가 아냐" -> “정상 대가 아냐”
  * 예: '故이예람 사건' -> ‘故이예람 사건’

[3. 본문 요약 구조 및 서술어 규칙]
- 본문 요약은 핵심 내용에 맞춰 3~4문장으로 작성한다.
- 첫 문장 시작 시에만 붙여 쓴 하이픈(-문장)을 사용하며, 문장 간에는 줄바꿈 없이 마침표(.)로만 연결한다.
- 모든 문장의 서술어는 평서형 종결을 생략하고 어근으로 마무리한다. (예: 선고, 기소, 구형, 기각, 기각 결정, 압수수색, 공판 진행, 수사 중 등 / ~함, ~했음 지양)
- 【타지】 단독 기사는 요약문 마지막 마침표(.) 바로 뒤에 줄바꿈 없이 한 칸 공백을 두고 ` →참고하겠습니다.`를 붙여 마무리한다.

[4. 시점 및 날짜 표기 절대 규칙 (세계일보 규정 - 최우선 반영)]
① 당월(현재 기준 {c_month}월) 내 일자 표기:
   - 현재 시점과 같은 달({c_month}월)의 날짜는 '월'을 절대 쓰지 않고 일자만 쓴다.
     * 잘못된 예: {c_month}월{c_day}일, {c_month}월 {c_day}일
     * 올바른 예: {c_day}일, 2일, 5일
   - 당월({c_month}월) 내에서 지나간 날짜나 다가오는 특정 일자를 가리킬 때는 '지난 N일' 대신 '이달 N일'로 표기한다. (단, 첫 문장의 단순 발생일은 'N일'로 쓴다)

② 올해({c_year}년) 지나간 월 표기:
   - 올해({c_year}년)의 지나간 달을 언급할 때는 반드시 '올 N월'로 표기하며 월과 일을 붙여 쓴다.
     * 예: {c_year}년 3월 -> '올 3월' (또는 '올 3월15일')

③ 과거 연도 표기:
   - 직전 연도({c_year - 1}년)는 '지난해'로 표기한다.
     * 예: {c_year - 1}년 3월 -> '지난해 3월'
   - 2년 전({c_year - 2}년) 및 그 이전 연도는 연도 숫자를 그대로 쓴다.
     * 예: {c_year - 2}년 3월 -> '{c_year - 2}년 3월'
   - 직전 달은 '지난달'로 표기한다.

④ 행위 시점과 전언 시점 구분 (사실 오해 방지):
   - 기사 서두의 전언 시점(예: "N일 법조계에 따르면", "N일 취재에 따르면")에 등장하는 날짜를 주어의 행위 날짜로 오인해 쓰지 않는다.
   - 주어가 해당 판결·결정·구형·제청 등을 실제로 행한 시점을 본문에서 찾아 기재한다.

⑤ 첫 문장 구조:
   - 반드시 `[주체], [실제 행위 발생 시점(위 규칙 적용)] [내용 요약(어근 마무리)].` 순으로 작성한다.
   - 첫 번째 문장의 주어 뒤에만 주격 조사(이/가/은/는)를 생략하고 쉼표(,)를 사용한다.
   - 두 번째 문장부터는 주격 조사와 보조사를 자연스럽게 정상 사용한다.

⑥ 기관별 주어 표기 세부 규칙:
   - 법원이 주어인 경우: 관할 법원, 재판부, 재판장을 포함한다.
     * 1심 합의부: '합의' 단어 삭제 및 '재판장' 표기 적용 (예: 서울중앙지법 형사22부(재판장 조형우))
     * 항소 재판부: 명칭 유지 (예: 서울고법 형사1부)
     * 단독·주심·영장전담: 이름 포함 (예: 서울중앙지법 형사5단독 000 판사 / 대법원 3부(주심 000 대법관))
   - 검찰이 주어인 경우: 구체적 검찰청 명시 (예: 서울중앙지검, 대전지검 등)

⑦ 호칭 및 수치:
   - 성씨+씨/모는 붙여 쓰고(정씨, 정명석씨), 직함은 띄어 쓴다.
   - 금액은 천 단위까지 숫자로 표기하며 쉼표(,)를 제거한다.
"""

def summarize_with_gemini(raw_report_text: str, api_keys: list = None) -> str:
    if not api_keys:
        raw_env = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY", "")
        api_keys = [k.strip() for k in raw_env.split(",") if k.strip()]

    if not api_keys:
        return "❌ 등록된 GEMINI_API_KEY가 없습니다."

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    system_instruction = build_system_instruction(now)

    last_err = None

    for idx, key in enumerate(api_keys):
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=raw_report_text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1
                )
            )
            cleaned = response.text.strip()
            lines = [line for line in cleaned.splitlines() if line.strip()]
            return "\n".join(lines)

        except Exception as e:
            err_str = str(e)
            last_err = e
            if "429" in err_str or "503" in err_str:
                time.sleep(1)
                continue
            raise e

    raise last_err
