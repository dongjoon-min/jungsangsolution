from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import uvicorn
import json
import os
import re

from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="kickthehurdle_dry_eye_symdrome")

# 테이블 가져오기
import pandas as pd
df = pd.read_excel(r'C:\Users\KTHD\Downloads\안구건조증 설계 ing.xlsx', sheet_name='solution_package')
df = df.set_index(['팩No.'])


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

    severe_list = ["7", "8", "9", "10"]

    if answers_dict.get(str(2), []) == "No" and any(item not in severe_list for item in answers_dict.get(str(3), [])) :
        next_question_id = 12  # "No"를 선택하면 question_id 11로 건너뜀
    elif question_id < 12:
        next_question_id = question_id + 1
    else:
        return RedirectResponse(url="/result", status_code=303)

    updated_answers = json.dumps(answers_dict)
    print (updated_answers)
    print (answers_dict)
    # print ("updated_answers", updated_answers)
    return templates.TemplateResponse(f"question{next_question_id}.html", {"request": request, "question_id": next_question_id, "answers": updated_answers})


@app.get("/question/{question_id}", response_class=HTMLResponse)
async def get_question(request: Request, question_id: int, answers: Optional[str] = None):
    if question_id < 1 or question_id > 11:
        return templates.TemplateResponse("index.html", {"request": request})
    
    answers_dict = json.loads(answers) if answers else {}
    answers_json = json.dumps(answers_dict)
    return templates.TemplateResponse(f"question{question_id}.html", {"request": request, "question_id": question_id, "answers": answers_json})

# result 

@app.get("/result", response_class=HTMLResponse)
async def display_result(request: Request, session: dict = Depends(get_session)):
    answers_json = session.get("answers", "{}")
    answers_dict = json.loads(answers_json)
    print (answers_dict)

    # 원인 판별 및 추가 메시지 로직
    cause_comments_list, solution_comments_list = process_causes(answers_dict)    
    tear_lack_score, tear_evaporate_score = type_score_calculate(answers_dict) 
    type_name, type_emoji, type_title, type_subtitle, type_detail_message = your_type_decision(tear_lack_score, tear_evaporate_score, answers_dict)
    pack1_package_name, pack1_package_gusang, pack1_selling_price, pack1_original_price, pack1_sentence, pack2_package_name, pack2_package_gusang, pack2_selling_price, pack2_original_price, pack2_sentence = recommend_pack(answers_dict, tear_evaporate_score, tear_lack_score)
    # print (answers_json)
    # print (cause_keywords)
    # print (special_message)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "answers": answers_dict,
        "cause_comments": cause_comments_list,
        "solution_comments": solution_comments_list,        

        "type_name" : type_name, 
        "type_emoji" : type_emoji, 
        "type_title" : type_title, 
        "type_subtitle" : type_subtitle,
        "type_detail_message" : type_detail_message,

        "tear_lack_score" : tear_lack_score,
        "tear_evaporate_score" : tear_evaporate_score,

        "pack1_package_name" : pack1_package_name, 
        "pack1_package_gusang" : pack1_package_gusang, 
        "pack1_original_price" : pack1_original_price,
        "pack1_selling_price" : pack1_selling_price,
        "pack1_sentence" : pack1_sentence,         

        "pack2_package_name" : pack2_package_name, 
        "pack2_package_gusang" : pack2_package_gusang, 
        "pack2_original_price" : pack2_original_price,       
        "pack2_selling_price" : pack2_selling_price,  
        "pack2_sentence" : pack2_sentence
    })

aged_list = ["40s", "50s", "60s"]

# 유형판별 함수
def type_score_calculate(answers_dict) :
    tear_lack_score = 0
    tear_evaporate_score = 0

    for key in range(3, 7):
        # answers_dict에서 해당 키의 값을 가져오고, 결과가 비어 있지 않은지 확인
        values = answers_dict.get(str(key), [])
        if values == "Yes":
            if key == 4:
                tear_lack_score += 5
            elif key == 5:
                tear_evaporate_score += 3
            elif key == 6:
                tear_evaporate_score += 3
            elif key == 7:
                tear_evaporate_score += 2

    for value in answers_dict.values():
        # 값을 콤마로 분리하여 리스트 생성
        splitted_values = value.split(',')
        # 각 분리된 값이 조건과 일치하는지 확인
        # print(splitted_values)
        
        if "VDT" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 1
        elif "2h" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 3
        elif "1h" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 2
        elif "space" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 1
        elif "weather" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 1
        elif "immune" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 2
            tear_lack_score += 2
        elif "symnerve" in [v.strip() for v in splitted_values] :
            tear_lack_score += 1
        elif "damage" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 1
        # question 11
        elif "sleep" in [v.strip() for v in splitted_values] :
            tear_lack_score += 2
        elif "stress" in [v.strip() for v in splitted_values] :
            tear_lack_score += 2
        elif "coffee" in [v.strip() for v in splitted_values] :
            tear_lack_score += 1            
        elif "isotretinoin" in [v.strip() for v in splitted_values] :
            tear_evaporate_score += 3

    print (tear_lack_score, tear_evaporate_score)
    return tear_lack_score, tear_evaporate_score
    
 # VDT, space, weather, coffee, immune, damage, symnerve, circulation
 # question 10 : circulation, thyroid, immune, isotretinoin, symnerve
 # question 11 : stress, sleep, stress, smoke

def your_type_decision(tear_lack_score, tear_evaporate_score, answers_dict) :
 
    severe_list = ['7', '8', '9', '10']

    if tear_evaporate_score <= 2 and tear_lack_score <= 2 :
        if any(item not in severe_list for item in answers_dict.get(str(3), [])) :
            type_name = "NOT_DES"
            type_emoji = "😅"
            type_title = "증상이 심하지 않다면, 지금부터 관리하면 늦지 않아요"
            type_subtitle = "눈을 마르지 않게 하는 생활습관을 실천하세요."
            type_detail_message = "아직 괜찮네~"
            return type_name, type_emoji, type_title, type_subtitle, type_detail_message
        else : 
            type_name = "COMPLEX_DES"
            type_emoji = "😱"
            type_title = "복합 안구건조 유형"
            type_subtitle = "눈물 생성 감소와, 눈물 증발이 복합되어 나타나요."
            type_detail_message = "눈 건조는 눈물 생성이 감소하거나, 아니면 눈물의 증발량이 늘어 생길 수 있어요. 눈물 생성이 감소하는 경우가 많지만, 때때로 눈물 층 구성의 변화나 마이봄샘의 기능 저하등으로 눈물의 증발량이 늘어서 생길 수도 있어요. 바람만 불어도 눈이 시리다면, 눈 표면을 보호하기 위해 안경을 착욯해주시는 것도 방법이에요."
            return type_name, type_emoji, type_title, type_subtitle, type_detail_message            
    elif (tear_lack_score - tear_evaporate_score) >= 3 :
        type_name = "LACK_DES"
        type_emoji = "😥"
        type_title = "눈물이 마르는 안구건조 유형"
        type_subtitle = "다양한 원인으로 인해 눈물 생성이 줄어든 경우에요."
        type_detail_message = "ㅠㅠ"
        return type_name, type_emoji, type_title, type_subtitle, type_detail_message
    elif (tear_evaporate_score - tear_lack_score) >= 3 :
        type_name = "EVAPORATE_DES"
        type_emoji = "😂"
        type_title = "눈물이 증발해버리는 안구건조 유형"
        type_subtitle = "눈물이 잘 나지만 눈이 말라요. 주로 마이봄샘의 기능이 저하된 경우에요."
        type_detail_message = "마이봄샘이란 눈꺼풀에서 지방을 분비하는 샘이에요. 마이봄샘에서 나오는 기름은 눈 표면에 얇은 막을 형성하여, 눈과 눈꺼풀의 움직임을 매끄럽게 해요. 하지만 마이봄샘이 막히거나 파괴, 변성 등 문제가 생기면 기름의 분비량이 줄고 기름의 성분이 불량해져 눈물이 쉽게 증발해요."
        return type_name, type_emoji, type_title, type_subtitle, type_detail_message
    else :
        type_name = "COMPLEX_DES"
        type_emoji = "😱"
        type_title = "복합 안구건조 유형"
        type_subtitle = "눈물 생성 감소와, 눈물 증발이 복합되어 나타나요."
        type_detail_message = "눈 건조는 눈물 생성이 감소하거나, 아니면 눈물의 증발량이 늘어 생길 수 있어요. 눈물 생성이 감소하는 경우가 많지만, 때때로 눈물 층 구성의 변화나 마이봄샘의 기능 저하등으로 눈물의 증발량이 늘어서 생길 수도 있어요. 바람만 불어도 눈이 시리다면, 눈 표면을 보호하기 위해 안경을 착용해주시는 것도 방법이에요."
        return type_name, type_emoji, type_title, type_subtitle, type_detail_message

# 유발요인 함수
def process_causes(answers_dict):
    cause_comments = ""
    solution_comments = "* 눈이 마르는 느낌이 들기 전에, 미리 <span class='highlight_1'>인공눈물</span>을 사용해주세요."

    if answers_dict.get("1", []) in aged_list:
        cause_comments += "* <span class='highlight_1'>40대 이상의 나이</span>는 눈물샘 기능을 저하시키고, 성호르몬에 의한 눈물 분비 촉진을 저해하여 눈을 건조하게 해요. 나이에 의한 안구건조증은 여성이 남성보다 흔해요."
        solution_comments += "* <span class='highlight_2'>루테인</span>은 눈 건조에 직접 도움이 되는 영양성분은 <span class='highlight_3'>아니지만</span>, <span class='highlight_2'>노화로 인한 황반색소의 밀도 감소</span>가 걱정된다면 섭취하실 수 있어요."

    for key in range(4, 8):
        # answers_dict에서 해당 키의 값을 가져오고, 결과가 비어 있지 않은지 확인
        values = answers_dict.get(str(key), [])
        if key == 5 and values == "Yes" and answers_dict.get("7", "") == "No" and answers_dict.get("8", "") == "None":
            cause_comments += "* <span class='highlight_1'>눈꺼풀 세정</span>이 필요할 수 있어요."
            solution_comments += "* 아직 사용해보시지 않았다면, <span class='highlight_2'>블레파졸 / 오큐소프트 등 눈꺼풀 세정제</span>를 사용해 보세요. * 눈 건조감 개선에, <span class='highlight_2'> 오메가3 성분이 풍부한 등푸른 생선 </span> 또는 <span class='highlight_2'>오메가3 영양제</span> 섭취가 도움될 수 있어요."
        elif values == "Yes":
            if key == 4:                
                cause_comments += "* <span class='highlight_1'>각막 주변 신경 손상</span>은, 눈물 분비를 촉진하는 신경을 무디게 하여 눈을 건조하게 해요."
                solution_comments += "* 눈을 자주 깜빡여주시고, 렌즈를 착용한다면 <span class='highlight_1'>렌즈보다는 안경</span>을 착용해주세요."            
            elif key == 5:
                cause_comments += "* <span class='highlight_1'>마이봄샘 변성, 파괴, 막힘</span>은 눈을 보호하는 지질층 형성을 어렵게 해요."
                solution_comments += "* 눈을 자주 깜빡여주시고, 렌즈를 착용한다면 <span class='highlight_1'>렌즈보다는 안경</span>을 착용해주세요. * 눈 건조감 개선에, <span class='highlight_2'> 오메가3 성분이 풍부한 등푸른 생선 </span> 또는 <span class='highlight_2'>오메가3 영양제</span> 섭취가 도움될 수 있어요. * 마이봄샘을 풀어주기 위해, <span class='highlight_2'>온열찜질</span>을 해볼 수 있어요."
            elif key == 6:
                cause_comments += "* <span class='highlight_1'>마이봄샘 변성, 파괴, 막힘</span>은 눈을 보호하는 지질층 형성을 어렵게 해요."
                solution_comments += "* 눈을 자주 깜빡여주시고, 렌즈를 착용한다면 <span class='highlight_1'>렌즈보다는 안경</span>을 착용해주세요. * 눈 건조감 개선에, <span class='highlight_2'> 오메가3 성분이 풍부한 등푸른 생선 </span> 또는 <span class='highlight_2'>오메가3 영양제</span> 섭취가 도움될 수 있어요. * 마이봄샘을 풀어주기 위해, <span class='highlight_2'>온열찜질</span>을 해볼 수 있어요."
            elif key == 7:
                solution_comments += "* 눈 건조감 개선에, <span class='highlight_2'> 오메가3 성분이 풍부한 등푸른 생선 </span> 또는 <span class='highlight_2'>오메가3 영양제</span> 섭취가 도움될 수 있어요. * 마이봄샘을 풀어주기 위해, <span class='highlight_2'>온열찜질</span>을 해볼 수 있어요."
                
    # print ("중간 cause_comments : ", cause_comments)

    cause_keyword_dic = {
        "2h": "* 스마트폰/모니터 사용 시간이 길면, <span class='highlight_1'>VDT 증후군</span>이 생길 수 있어요. 눈을 깜빡이는 횟수가 줄어 눈 건조가 심해져요.",
        "space": "* <span class='highlight_1'>실내 공기 오염</span> 으로 인한 마이봄샘 오염 또는 <span class='highlight_1'>건조한 실내 공기</span>로 인해 눈이 건조할 수 있어요.",
        "weather": "* <span class='highlight_1'>건조한 겨울철 날씨</span> 또는 <span class='highlight_1'>미세먼지</span>에 의해 <span class='highlight_1'>마이봄샘이 오염</span> 되었을 수 있어요.",
        "immune": "* <span class='highlight_1'>자가면역질환</span>으로 눈 주변 염증 및 표면 손상 가능성이 있어요",
        "circulation": "* <span class='highlight_1'>고혈압 등 순환계 질환</span>, <span class='highlight_1'>당뇨병</span> 등 혈액순환을 저해하는 질환은, 눈 주변 모세혈관의 혈액흐름을 방해하여 안구건조를 촉진해요.",
        "damage": "* <span class='highlight_1'>각막 주변 신경 손상</span>은, 눈물 분비를 촉진하는 신경을 무디게 하여 눈 건조를 촉진해요.",
        "symnerve": "* <span class='highlight_1'>교감신경이 항진</span>되거나 <span class='highlight_1'>스트레스가 누적</span>되면 눈물 생성이 줄어요.",
        "stress": "* <span class='highlight_1'>교감신경이 항진</span>되거나 <span class='highlight_1'>스트레스가 누적</span>되면 눈물 생성이 줄어요.",
        "sleep": "* <span class='highlight_1'>수면 시간이 부족</span>하면 눈물 생성이 줄어요",
        "isotretinoin" : "* 피지조절제로 복용하는 <span class='highlight_3'>이소트레티노인</span> 성분의 의약품은 마이봄샘의 지질 분비를 억제하여 눈을 건조하게 만들어요."
    }

    # thyroid는 원인 유발 코멘트 X

    solution_keyword_dic = {
        "2h": "* 야간 모니터 사용을 줄여주세요. 스마트폰이나 윈도우에서 제공하는 <span class='highlight_1'>야간 모드나 다크 모드</span>를 사용해 보세요. * 눈의 긴장을 풀기 위해 <span class='highlight_1'>20분마다 6m(20피트) 이상 떨어져 있는 대상을 20초 정도 바라보는 '20-20-20 운동'</span> 을 추천해요.",
        "space": "* <span class='highlight_1'>가습기, 공기청정기 등 실내 공기 질 및 습도 개선을 위한 수단</span>을 활용해 보세요.",
        "weather": "* 미세먼지가 심하거나 바람이 심하게 부는 날에는, 눈을 보호할 수 있는 안경을 착용하시거나 야외에 있는 시간을 줄여주세요.",
        "immune":  "* 기저질환이 잘 관리되면, 부수적으로 눈 건조 완화에 도움이 될 수 있어요.",
        "damage": "* 기저질환이 잘 관리되면, 부수적으로 눈 건조 완화에 도움이 될 수 있어요.",
        "symnerve": "* <span class='highlight_1'>교감신경 항진</span> 및 <span class='highlight_1'>누적된 스트레스</span>를 줄이기 위해 <span class='highlight_2'>마그네슘, 레시틴 등 영양제</span>를 섭취할 수 있어요.",
        "circulation" : "* 기저질환이 잘 관리되면, 부수적으로 눈 건조 완화에 도움이 될 수 있어요.",
        "stress": "* <span class='highlight_1'>교감신경 항진</span> 및 <span class='highlight_1'>누적된 스트레스</span>를 줄이기 위해 <span class='highlight_2'>마그네슘, 레시틴 등 영양제</span>를 섭취할 수 있어요.",
        "sleep": "* <span class='highlight_1'>수면 시간</span>을 늘려주세요. 적정 수면 시간은 7~8시간이에요.",
        "isotretinoin" : "* <span class='highlight_3'>이소트레티노인의 건조 부작용이 심할 경우 처방해주신 의사선생님과 복용량 및 복용 여부에 대해 상담</span>하세요. * <span class='highlight_3'>이소트레티노인 의약품을 복용하는 동안에는, 눈이 건조해도 비타민 A 영양제 섭취는 피하는 것</span>이 좋아요."
    }

    for condition, keyword in cause_keyword_dic.items():
        for value in answers_dict.values():
            # 값을 콤마로 분리하여 리스트 생성
            splitted_values = value.split(',')
            # 각 분리된 값이 조건과 일치하는지 확인            
            if condition in [v.strip() for v in splitted_values]:  # 공백 제거 후 비교
                cause_comments += keyword
    
    for condition, keyword in solution_keyword_dic.items():
        for value in answers_dict.values():
            # 값을 콤마로 분리하여 리스트 생성
            splitted_values = value.split(',')
            # 각 분리된 값이 조건과 일치하는지 확인
            if condition in [v.strip() for v in splitted_values]:  # 공백 제거 후 비교
                solution_comments += keyword

    # 위 for구문 다 돌렸는데도 아무런 코멘트 추가가 없을 경우
    if cause_comments == "" :
       cause_comments += "* 안구건조감이 없고 불편감도 적다고 응답해주셔서, 현재 응답으로는 추정하기 어려워요."

    if solution_comments == "* 눈이 마르는 느낌이 들기 전에, 미리 <span class='highlight_1'>인공눈물</span>을 사용해주세요." :
       solution_comments += "* 혹시 눈이 마르는 느낌이 든다면, <span class='highlight_1'>인공눈물</span>을 미리 사용해주세요. * 모니터/스마트폰을 장시간 본다면, 중간중간 눈을 의식하여 깜빡여주세요. * 눈이 긴장된다면, <span class='highlight_1'>20분마다 6m(20피트) 이상 떨어져 있는 대상을 20초 정도 바라보는 '20-20-20 운동'</span> 을 추천해요. * "

    # * 단위로 스플릿
    cause_comments_list = list(set([item.strip() for item in cause_comments.split('*') if item.strip()]))
    solution_comments_list = list(set([item.strip() for item in solution_comments.split('*') if item.strip()]))

    # print (cause_comments_list)
    return cause_comments_list, solution_comments_list


# def highlight_keywords(cause_keywords_list, keywords):
#     highlight_keywords = ['VDT 증후군', '실내 공기 오염', '건조한 겨울철 날씨', '건조한 실내 공기' '자가면역질환', '교감신경이 항진','스트레스 누적', '수면 부족 또는 수면 장애']
#     # 키워드를 정규 표현식 패턴으로 변환
#     pattern = r'\b(' + '|'.join(re.escape(keyword) for keyword in keywords) + r')\b'
#     # 텍스트 내에서 키워드 찾아 강조
#     highlighted_text = re.sub(pattern, r'<span class="highlight">\1</span>', text, flags=re.IGNORECASE)
#     return highlighted_text

# # 데이터 딕셔너리 내의 모든 텍스트 항목에 대해 키워드 강조 함수 적용
# for key, value in data.items():
#     data[key] = highlight_keywords(value, keywords)



# 장문 함수
# def determine_age_message(answers_dict):
#     special_message = ""
#     age_answer = answers_dict.get("1", [])
#     age_messages = {
#         "40s": "40대 이상부터는 힘들죠 ㅠㅠ",
#         "50s": "당신은 50대입니다. 이 연령대에 적합한 건강 관리 팁을 제공해 드립니다.",
#         "60s": "당신은 60대 이상입니다. 이 연령대에 적합한 건강 관리 팁을 제공해 드립니다."
#     }
#     for age, message in age_messages.items():
#         if age in age_answer:
#             special_message = message
#             break
#     return special_message

# 팩 유형 함수
def recommend_pack(answers_dict, tear_evaporate_score, tear_lack_score) :

    pack1_dic = {
        1 : "팩1",
        2 : "팩2",
        5 : "팩5",
        7 : "팩7",
        8 : "팩8",
        12 : "팩12"
    }
    
    pack2_dic = {
       3 : "팩3",
       4 : "팩4",
       6 : "팩6",
       9 : "팩9",
       10 : "팩10",
       11 : "팩11"
    }    

    # 팩 노출 우선순위 정하기 전처리
    pack_decide_values_list = []
    for value in answers_dict.values():
        # 값을 콤마로 분리하여 리스트 생성
        splitted_values = value.split(',')
        # 각 분리된 값이 조건과 일치하는지 확인
        for item in splitted_values:
            pack_decide_values_list.append(item.strip())  # 공백 제거 후 추가
    print(pack_decide_values_list)
    # 팩1 노출순위 정하기
    if "isotretinoin" in pack_decide_values_list :
        pack1 = pack1_dic[12]
    elif "5" in answers_dict and answers_dict["5"] == "Yes" or \
         "6" in answers_dict and answers_dict["6"] == "Yes":
        if "7" in answers_dict and answers_dict["7"] == "No":
            pack1 = pack1_dic[7]
        elif "7" in answers_dict and answers_dict["7"] == "Yes":
            pack1 = pack1_dic[8]
    elif any(v in pack_decide_values_list for v in ["stress", "caffeine"]):
        pack1 = pack1_dic[2]
    elif "sleep" in pack_decide_values_list :
        pack1 = pack1_dic[5]
    else : 
        pack1 = pack1_dic[1]

    # 팩2 노출순위 정하기
    if "isotretinoin" in pack_decide_values_list :
        pack2 = pack2_dic[11]   
    elif tear_evaporate_score + tear_lack_score > 5 and "sleep" not in pack_decide_values_list :
        pack2 = pack2_dic[9]
    elif "sleep" in pack_decide_values_list :
        pack2 = pack2_dic[6]
    elif "smoke" in pack_decide_values_list :
        pack2 = pack2_dic[10]
    elif any(age in pack_decide_values_list for age in aged_list) :
        pack2 = pack2_dic[3]
    else : 
        pack2 = pack2_dic[4]

    pack1_package_name = df.loc[pack1]['패키지명']
    pack1_package_gusang = df.loc[pack1]['패키지 구성']
    pack1_selling_price = df.loc[pack1]['판매가격']
    pack1_original_price = df.loc[pack1]['매입가 + 핏타민 소분 판매가 \n(0% 할인 기준)']
    pack1_sentence = df.loc[pack1]['추천 사유']
    print (pack1, pack1_package_name)

    pack2_package_name = df.loc[pack2]['패키지명']
    pack2_package_gusang = df.loc[pack2]['패키지 구성']
    pack2_selling_price = df.loc[pack2]['판매가격']
    pack2_original_price = df.loc[pack2]['매입가 + 핏타민 소분 판매가 \n(0% 할인 기준)']
    pack2_sentence = df.loc[pack2]['추천 사유']
    print (pack2, pack2_package_name)
    return pack1_package_name, pack1_package_gusang, pack1_selling_price, pack1_original_price, pack1_sentence, pack2_package_name, pack2_package_gusang, pack2_selling_price, pack2_original_price, pack2_sentence

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
