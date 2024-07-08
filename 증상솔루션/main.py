from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import uvicorn
import json
import os

from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

# 현재 파일의 디렉토리 경로를 기준으로 templates 디렉토리 설정
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
# print(f"Templates directory: {templates_dir}")  # 디버깅을 위해 추가
templates = Jinja2Templates(directory=templates_dir)

def get_session(request: Request):
    return request.session


# 정적 파일 경로 설정
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/submit/{question_id}", response_class=HTMLResponse)
async def submit_answers(request: Request, question_id: int, answer: str = Form(...), existing_answers: Optional[str] = Form(""), session: dict = Depends(get_session)):
    if existing_answers:
        try:
            answers_dict = json.loads(existing_answers)
        except json.JSONDecodeError:
            answers_dict = {}
    else:
        answers_dict = {}

    answers_dict[str(question_id)] = answer  # question_id를 문자열로 변환하여 딕셔너리 키로 사용

    # print("정답모음 dic : ", answers_dict)  # 디버깅을 위해 추가
    # print("마지막 answers : ", answer)  # 디버깅을 위해 추가
    session["answers"] = json.dumps(answers_dict)

    if question_id == 2 and "No" in answers_dict.values():
        next_question_id = 8  # "No"를 선택하면 question_id 8로 건너뜀
    elif question_id < 10:
        next_question_id = question_id + 1
    else:
        return RedirectResponse(url="/result", status_code=303)

    updated_answers = json.dumps(answers_dict)
    # print ("updated_answers", updated_answers)
    return templates.TemplateResponse(f"question{next_question_id}.html", {"request": request, "question_id": next_question_id, "answers": updated_answers})


@app.get("/question/{question_id}", response_class=HTMLResponse)
async def get_question(request: Request, question_id: int, answers: Optional[str] = None):
    if question_id < 1 or question_id > 10:
        return templates.TemplateResponse("index.html", {"request": request})
    
    answers_dict = json.loads(answers) if answers else {}
    answers_json = json.dumps(answers_dict)
    print ("answers_json", answers_json)
    return templates.TemplateResponse(f"question{question_id}.html", {"request": request, "question_id": question_id, "answers": answers_json})



# result 

@app.get("/result", response_class=HTMLResponse)
async def display_result(request: Request, session: dict = Depends(get_session)):
    answers_json = session.get("answers", "{}")
    answers_dict = json.loads(answers_json)

    # 원인 판별 및 추가 메시지 로직
    cause_keywords = process_causes(answers_dict)
    special_message = determine_age_message(answers_dict)
    tear_lack_score, tear_evaporate_score = type_score_calculate(answers_dict) 
    type_name, type_title, type_subtitle = your_type_decision(tear_lack_score, tear_evaporate_score)
    # print (answers_json)
    # print (cause_keywords)
    # print (special_message)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "answers": answers_dict,
        "cause_keywords": cause_keywords,
        "special_message": special_message,
        "type_name" : type_name, 
        "type_title" : type_title, 
        "type_subtitle" : type_subtitle,
        "tear_lack_score" : tear_lack_score,
        "tear_evaporate_score" : tear_evaporate_score,
    })


# 유형판별 함수
def type_score_calculate(answers_dict) :
    tear_lack_score = 0
    tear_evaporate_score = 0

    for key in range(3, 7):
        # answers_dict에서 해당 키의 값을 가져오고, 결과가 비어 있지 않은지 확인
        values = answers_dict.get(str(key), [])
        if values == "Yes":
            if key == 3:
                tear_lack_score += 5
            elif key == 4:
                tear_evaporate_score += 5
            elif key == 5:
                tear_evaporate_score += 2
            elif key == 6:
                tear_evaporate_score += 2

    for value in answers_dict.values():
        # 값을 콤마로 분리하여 리스트 생성
        splitted_values = value.split(',')
        # 각 분리된 값이 조건과 일치하는지 확인
        print(splitted_values)
        
        if "VDT" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 1
        elif "space" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 1
        elif "weather" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 1
        elif "immune" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 2
            tear_lack_score += 2
        elif "symnerve" in [v.strip() for v in splitted_values] :
            tear_lack_score += 3
        elif "sleep" in [v.strip() for v in splitted_values] :
            tear_lack_score += 1
        elif "stress" in [v.strip() for v in splitted_values] :
            tear_lack_score += 1
        elif "damage" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 1

    print (tear_lack_score, tear_evaporate_score)
    return tear_lack_score, tear_evaporate_score
    
 # VDT, space, weather, coffee, immune, damage, symnerve, circulation, sleep, stress, smoke

def your_type_decision(tear_lack_score, tear_evaporate_score) :
    
    type_name = ""
    type_title = ""
    type_subtitle = ""
 
    if tear_evaporate_score <= 1 and tear_lack_score <= 1 :
        type_name = "NOT_DES"
        type_title = "증상이 심하지 않다면, 지금부터 관리하면 늦지 않아요"
        type_subtitle = "눈을 마르지 않게 하는 생활습관을 실천하세요."
        return type_name, type_title, type_subtitle
    elif (tear_lack_score - tear_evaporate_score) > 2 :
        type_name = "LACK_DES"
        type_title = "눈물이 마르는 안구건조 유형"
        type_subtitle = "다양한 원인으로 인해 눈물 생성이 줄어든 경우에요."
        return type_name, type_title, type_subtitle
    elif (tear_evaporate_score - tear_lack_score) > 2 :
        type_name = "EVAPORATE_DES"
        type_title = "눈물이 증발해버리는 안구건조 유형"
        type_subtitle = "눈물이 잘 나도 눈이 마르거나, 마이봄샘의 기능이 저하된 경우에요."
        return type_name, type_title, type_subtitle
    else :
        type_name = "COMPLEX_DES"
        type_title = "복합 안구건조 유형"
        type_subtitle = "눈물 생성 감소와, 눈물 증발이 복합되어 나타나는 경우에요."
        return type_name, type_title, type_subtitle
    



# 유발요인 함수
def process_causes(answers_dict):
    cause_keywords = ""
    if answers_dict.get("1", []) in ["40s", "50s", "60s"]:
        cause_keywords += "* 40대 이상 (노화)"
    
    for key in range(3, 7):
        # answers_dict에서 해당 키의 값을 가져오고, 결과가 비어 있지 않은지 확인
        values = answers_dict.get(str(key), [])
        if values == "Yes":
            if key == 3:
                tear_lack_score += 1
                cause_keywords += "* 시력교정술 * 장시간의 렌즈 착용"
            elif key == 4:
                cause_keywords += "* 눈물 증발 증가"
            elif key == 5:
                cause_keywords += "* 마이봄샘 이상"
            elif key == 6:
                cause_keywords += "* 마이봄샘 막힘"
    # print ("중간 cause_keywords : ", cause_keywords)

    cause_keyword_dic = {
        "2h": "* 스마트/모니터 사용 시간이 길면, VDT 증후군이 생길 수 있어요.",
        "space": "* 실내 공기 오염으로 인한 마이봄샘 오염 * 건조한 실내 공기",
        "weather": "* 건조한 겨울철 날씨 * 미세먼지에 의한 마이봄샘 오염",
        "immune": "* 자가면역질환에 의한 가능성이 있어요 (쇼그렌증후군, 마이봄샘 파괴 등)",
        "damage": "* 각막 주변의 신경이 손상되면, 눈물 분비를 촉진하는 신경을 무뎌져 안구건조감을 유발해요.",
        "symnerve": "* 교감신경이 항진되면 눈물 생성이 줄어들어요.",
        "circulation":"* 고혈압 등 관상동맥질환은 어쩌구 저쩌구해서 안구건조 유발",
        "stress": "* 스트레스 누적",
        "sleep": "* 수면 부족 또는 수면 장애"
    }

    for condition, keyword in cause_keyword_dic.items():
        for value in answers_dict.values():
            # 값을 콤마로 분리하여 리스트 생성
            splitted_values = value.split(',')
            # 각 분리된 값이 조건과 일치하는지 확인
            if condition in [v.strip() for v in splitted_values]:  # 공백 제거 후 비교
                cause_keywords += keyword
    print (cause_keywords)
    cause_keywords_list = [item.strip() for item in cause_keywords.split('*') if item.strip()]

    return cause_keywords_list

def determine_age_message(answers_dict):
    special_message = ""
    age_answer = answers_dict.get("1", [])
    age_messages = {
        "40s": "40대 이상부터는 힘들죠 ㅠㅠ",
        "50s": "당신은 50대입니다. 이 연령대에 적합한 건강 관리 팁을 제공해 드립니다.",
        "60s": "당신은 60대 이상입니다. 이 연령대에 적합한 건강 관리 팁을 제공해 드립니다."
    }
    for age, message in age_messages.items():
        if age in age_answer:
            special_message = message
            break
    return special_message















# @app.post("/result", response_class=HTMLResponse)
# async def result(request: Request, answers: str):
#     answers_dict = json.loads(answers)
#     print("Decoded answers_dict:", answers_dict)
#     # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 원인 판별하기 !!!!!!!!!!!!!!!!!!!!!!!!!!!!
#     cause_keywords = ""
#     if answers_dict.get("1", []) in ["40s", "50s", "60s"] :
#         cause_keywords += "* 노화 (40대 이상)"

#     # 각 키 값에 대해 다른 메시지 추가
#     for key in range(2, 7):
#         if answers_dict.get(str(key), [])[0] == "Yes":
#             if key == 3:
#                 cause_keywords += "* 시력교정술 * 장시간의 렌즈 착용"
#             elif key == 4:
#                 cause_keywords += "* 눈물 증발 증가"
#             elif key == 5:
#                 cause_keywords += "* 마이봄샘 이상"
#             elif key == 6:
#                 cause_keywords += "* 마이봄샘 막힘"

    



#     # if "VDT" in answers_dict.values() :
#     #     cause_keywords += "* VDT 증후군"
#     # if "space" in answers_dict.values() :
#     #     cause_keywords += "* 실내 공기 오염"
#     # if "weather" in answers_dict.values() :
#     #     cause_keywords += "* 외부 환기"
#     # if "immune" in answers_dict.values() :
#     #     cause_keywords += "* 자가면역질환에 의한 눈 손상 * 갑상선 질환"
#     # if "damage" in answers_dict.values() :
#     #     cause_keywords += "* 질환에 의한 눈 손상"

    
#

#     # 나의 안구건조증의 원인은
#     cause_keywords = {
#         "40s" : "노화",
#         "50s" : "노화",
#         "60s" : "노화",
#     } 

#     # 연령대별 메시지 딕셔너리
#     age_messages = {
#         "40s": "40대 이상부터는 힘들죠 ㅠㅠ",
#         "50s": "당신은 50대입니다. 이 연령대에 적합한 건강 관리 팁을 제공해 드립니다.",
#         "60s": "당신은 60대 이상입니다. 이 연령대에 적합한 건강 관리 팁을 제공해 드립니다."
#     }

#     all_answers = [item for sublist in answers_dict.values() for item in sublist]
#     print ("이것은 리스트로 바꾼", all_answers)

#     print (cause_keywords, special_message)

#     # 특정 조건에 따른 메시지 추가
#     special_message = ""
#     age_answer = answers_dict.get("1", [])
#     for age, message in age_messages.items():
#         if age in age_answer:
#             special_message = message
#             break

#     return templates.TemplateResponse("result.html", {
#         "request": request,
#         "answers": answers_dict,
#         "cause_keywords" : cause_keywords,
#         "special_message": special_message
#     })


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
