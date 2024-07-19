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

    if answers_dict.get(str(2), []) == "No" and answers_dict.get(str(3), []) == "No" and any(item not in severe_list for item in answers_dict.get(str(4), [])) :
       return RedirectResponse(url="/result", status_code=303)
    elif question_id < 13:
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
    if question_id < 1 or question_id > 13:
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
    cause_keywords_list, cause_comments_list, solution_comments_list = process_causes(answers_dict)    
    tear_lack_score, tear_evaporate_score = type_score_calculate(answers_dict) 
    type_name, type_emoji, type_title, type_subtitle, type_img_src, type_detail_message = your_type_decision(tear_lack_score, tear_evaporate_score, answers_dict)
    pack1_package_name, pack1_package_gusang, pack1_selling_price, pack1_original_price, pack1_sentence, pack2_package_name, pack2_package_gusang, pack2_selling_price, pack2_original_price, pack2_sentence = recommend_pack(answers_dict, tear_evaporate_score, tear_lack_score)
    # print (answers_json)
    # print (cause_keywords)
    # print (special_message)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "answers": answers_dict,
        "cause_keywords" : cause_keywords_list,
        "cause_comments": cause_comments_list,
        "solution_comments": solution_comments_list,        

        "type_name" : type_name, 
        "type_emoji" : type_emoji, 
        "type_title" : type_title, 
        "type_subtitle" : type_subtitle,
        "type_img_src" : type_img_src,
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

    # 페이지 5,6 : 증발 점수에 해당
    Yes_mapping = {
        'Yes': {5: 4, 6: 4}
    }

    # 페이지 5,6 : Yes에 해당하는 경우 증발 점수 부여
    for key in range(5, 7):
        value = answers_dict.get(str(key), "")
        tear_evaporate_score += Yes_mapping.get(value, {}).get(key, 0)
    
    # Separate mappings for lack and evaporate scores
    lack_keyword_mapping = {
        "sleep": 2, "stress": 2, "coffee": 1,
        "immune": 2, "tinnitus": 2, "headache": 1, "mucous": 1,
        "antihistamine": 2, "antidepressant": 1, "digestive": 1,
        "surgery1": 2, "surgery2": 2, "lasiklasec": 2
    }

    evaporate_keyword_mapping = {        
        "40s": 3, "50s": 4, "60s": 4,
        "sight" : 1, "burning" : 1, "soreness" : 1, "swell" : 1,                 
        "2h": 4, "1h": 2, "space": 1, "wind": 1, "aircon": 1,
        "immune": 2, "isotretinoin": 4
    }
    
    for value in answers_dict.values():
        keywords = [v.strip() for v in value.split(',')]
        for keyword in keywords:
            tear_lack_score += lack_keyword_mapping.get(keyword, 0)
            tear_evaporate_score += evaporate_keyword_mapping.get(keyword, 0)

    print(tear_lack_score, tear_evaporate_score)
    return tear_lack_score, tear_evaporate_score


# 유형 결정 클래스 및 출력 메시지들
class DryEyeType:
    def __init__(self):
        self.type_name = ""
        self.type_emoji = ""
        self.type_title = ""
        self.type_image_src = ""
        self.type_subtitle = ""
        self.type_detail_message = ""

    def get_info(self):
        return self.type_name, self.type_emoji, self.type_title, self.type_subtitle, self.type_image_src, self.type_detail_message


class NotDes(DryEyeType):
    def __init__(self):
        self.type_name = "NOT_DES"
        self.type_emoji = "😅"
        self.type_title = "증상이 심하지 않다면, 지금부터 관리하면 늦지 않아요"
        self.type_subtitle = "눈을 마르지 않게 하는 생활습관을 실천하세요."
        self.type_image_src = "https://raw.githubusercontent.com/dongjoon-min/publicimages/main/images/%EB%A7%88%EC%9D%B4%EB%B4%84%EC%83%98.PNG"
        self.type_detail_message = ("건강보험공단 데이터베이스에 따르면, 우리나라에서 안구건조증의 발생률은"
                                    "2010년 약 8%에서 2021년에는 약 17%로 증가 추세이며, 성인에서는 약 30%에요."
                                    "스마트폰 등 디지털기기의 사용이 늘면서 안구건조증으로 진료받는 환자가 매년 약 250만 명에 이르러요."
                                    "미리 눈 건조를 예방하는 생활습관을 길러 보세요.")

class ComplexDes(DryEyeType):
    def __init__(self):
        self.type_name = "COMPLEX_DES"
        self.type_emoji = "😱"
        self.type_title = "복합 안구건조 유형"
        self.type_subtitle = "눈물 생성 감소와, 눈물 증발이 복합되어 나타나요."
        self.type_image_src = "https://raw.githubusercontent.com/dongjoon-min/publicimages/main/images/%EB%A7%88%EC%9D%B4%EB%B4%84%EC%83%98.PNG"
        self.type_detail_message = ("눈 건조는 눈물 생성이 감소하거나, 아니면 눈물의 증발량이 늘어 생길 수 있어요."
                                    "눈물 생성이 감소하는 경우가 많지만, 때때로 눈물 층 구성의 변화나 마이봄샘의 기능 저하등으로 "
                                    "눈물의 증발량이 늘어서 생길 수도 있어요. 바람만 불어도 눈이 시리다면, 눈 표면을 보호하기 위해 "
                                    "안경을 착용해주시는 것도 방법이에요.")
        
class LackDes(DryEyeType):
    def __init__(self):
        self.type_name = "LACK_DES"
        self.type_emoji = "😥"
        self.type_title = "눈물이 마른 안구건조 유형"        
        self.type_subtitle = "다양한 원인으로 인해 눈물 생성이 줄어 눈이 건조해졌을 수 있어요."
        self.type_image_src = "https://raw.githubusercontent.com/dongjoon-min/publicimages/main/images/%EB%A7%88%EC%9D%B4%EB%B4%84%EC%83%98.PNG"
        self.type_detail_message = ("<span class='highlight_1'>눈물샘의 기능이 저하</span>되거나, <span class='highlight_1'>눈물 생성을 자극하는 신경의 기능 저하</span>로 눈물 생성이 줄어요."
                                      "약물 중에서는 <span class='highlight_1'>항히스타민제, 진경제, 항콜린제</span> 등이 원인이 될 수 있어요.")


class EvaporateDes(DryEyeType):
    def __init__(self):
        self.type_name = "EVAPORATE_DES"
        self.type_emoji = "😂"        
        self.type_title = "눈물이 증발하는 안구건조 유형"
        self.type_subtitle = "눈물이 잘 생성됨에도 눈이 마르는 유형, 주로 마이봄샘의 기능이 저하된 경우에요."
        self.type_image_src = "https://raw.githubusercontent.com/dongjoon-min/publicimages/main/images/%EB%A7%88%EC%9D%B4%EB%B4%84%EC%83%98.PNG"
        self.type_detail_message = ("<span class='highlight_1'>마이봄샘</span>이란 눈꺼풀에서 지방을 분비하는 샘이에요. 마이봄샘에서 나오는 기름은 눈 표면에 얇은 막을 형성하여, "
                                    "눈과 눈꺼풀의 움직임을 매끄럽게 해요. 하지만 <span class='highlight_1'>마이봄샘이 막히거나 파괴, 변성 등 문제가 생기면 기름의 분비량이 줄고, 기름의 성분이 불량해져 눈물이 쉽게 증발</span>해요.")

        # self.type_imgsrc : 이미지 추가


# 유형 결정 로직
def your_type_decision(tear_lack_score, tear_evaporate_score, answers_dict):
    severe_list = ['6', '7', '8', '9', '10']

    def is_not_severe():
        return any(item not in severe_list for item in answers_dict.get(str(4), []))

    if tear_evaporate_score <= 2 and tear_lack_score <= 2:
        if is_not_severe():
            return NotDes().get_info()
        else:
            return ComplexDes().get_info()
    elif (tear_lack_score - tear_evaporate_score) >= 5:
        return LackDes().get_info()
    elif tear_lack_score <= 4 and (tear_evaporate_score - tear_lack_score) >= 3:
        return EvaporateDes().get_info()
    else:
        return ComplexDes().get_info()
    


# # 질문 2
# value_question2_list = ["dryness", "sand", "red", "pain", "light", "No"]
# # 질문 3
# value_question3_list = ["sight", "burning", "soreness", 'swell', "No"]
# # 질문 5
# value_onjjimjil_list = ['Yes', 'No', "notyet"]
# # 질문 6
# value_blepasol_list = ['Yes', 'No', "notyet"]
# # 질문 9
# value_circumstance_list = ["wind", "aircon", "space", "getup", "cosmetics", "None"]
# # 질문 11
# value_medication_list = ["antihistamine","antidepressant","digestive","None"]
# # 질문 12
# value_disease_list = ["circulation", "diabetes", "thyroid", "immune", "tinnitus", "headache", "mucous", "None"]

# 유발요인 함수
def process_causes(answers_dict):
    cause_keywords = ""
    cause_comments = ""
    solution_comments = "* 눈이 마르는 느낌이 들기 전에, 미리 <span class='highlight_1'>인공눈물</span>을 사용해주세요."

    if answers_dict.get("1", []) in aged_list:
        cause_keywords += "40대 이상의 나이"
        cause_comments += "* <span class='highlight_1'>40대 이상의 나이</span>는 눈물샘 기능을 저하시키고, 성호르몬에 의한 눈물 분비 촉진을 저해하여 눈을 건조하게 해요. 나이에 의한 안구건조증은 여성이 남성보다 흔해요."
        solution_comments += "* <span class='highlight_2'>루테인</span>은 눈 건조에 직접 도움이 되는 영양성분은 <span class='highlight_3'>아니지만</span>, <span class='highlight_2'>노화로 인한 황반색소의 밀도 감소</span>가 걱정된다면 섭취하실 수 있어요."

    # print ("중간 cause_comments : ", cause_comments)

    cause_keyword_dic = {
        "2h" : "* VDT 증후군",

        "space" : "* 실내 환경",
        "wind": "* 바람에 무너지는 불안정한 눈물막",
        "aircon" : "* 바람에 무너지는 불안정한 눈물막",
        "getup" : "* 눈 뜨고 취침",
        "cosmetics" : "* 화장품 자극",
        
        "immune": "* 자가면역질환",
        "circulation": "* 순환계 질환",
        "symnerve": "* 스트레스 누적 * 교감신경 항진",
        "diabetes": "* 순환계 질환",
        "tinnitus" : "* 스트레스 누적 * 교감신경 항진",

        "isotretinoin" : "* 이소트레티노인 의약품 복용",

        "lasiklasec" : "* 눈 수술",
        "surgery1" : "* 눈 수술",
        "surgery2" : "* 눈 수술",
        "lens" : "* 장시간 렌즈 착용",

        "antihistamine" : "* 항히스타민제 복용",
        "antidepressant" : "* 항우울제 복용",        
        "digestive" : "* 진경제 복용",

        "stress": "* 스트레스 누적 * 교감신경 항진",
        "sleep": "* 수면 부족"
    }

    cause_comments_dic = {
        "2h":           "* 스마트폰/모니터 사용 시간이 길면, <span class='highlight_1'>VDT 증후군</span>이 생길 수 있어요. 영상 기기를 사용하며 눈을 깜빡이는 횟수가 줄어 눈 건조가 심해져요.",

        "space":        "* <span class='highlight_1'>실내 공기 오염</span> 으로 인한 마이봄샘 오염 또는 <span class='highlight_1'>건조한 실내 공기</span>로 인해 눈이 건조할 수 있어요.",
        "weather":       "* <span class='highlight_1'>건조한 겨울철 날씨</span> 또는 <span class='highlight_1'>미세먼지</span>에 의해 <span class='highlight_1'>마이봄샘이 오염</span> 되었을 수 있어요.",
        "aircon":       "* <span class='highlight_1'>건조한 겨울철 날씨</span> 또는 <span class='highlight_1'>미세먼지</span>에 의해 <span class='highlight_1'>마이봄샘이 오염</span> 되었을 수 있어요.",
        "getup" :       "* 자고 일어났을 때 유독 눈이 건조하다면, <span class='highlight_1'>자는 동안 눈을 완전히 감지 않았을 수 있어요. '야행성 토안'</span> 이라고도 불러요. 눈 수술 이후에도 눈 주변 근육 수축 기능 저하로 일시적으로 생길 수 있어요.",
        "cosmetics" :   "* 눈 주변에 사용하는 화장품이 원인일 수 있어요. 자극이 덜한 제품으로 바꾸거나, 눈에 직접 닿지 않게 사용해 주세요.",

        "lasiklasec":       "* <span class='highlight_1'>각막 주변 신경 손상</span>은, 눈물 분비를 촉진하는 신경을 무디게 하여 눈 건조를 촉진해요.",
        "surgery1":       "* <span class='highlight_1'>각막 주변 신경 손상</span>은, 눈물 분비를 촉진하는 신경을 무디게 하여 눈 건조를 촉진해요.",
        "surgery2":       "* <span class='highlight_1'>각막 주변 신경 손상</span>은, 눈물 분비를 촉진하는 신경을 무디게 하여 눈 건조를 촉진해요.",
        "lens" :        "* 장시간의 렌즈 착용은 눈물막 안정성을 떨어트려요. * <span class='highlight_1'>각막 주변 신경 손상</span>은, 눈물 분비를 촉진하는 신경을 무디게 하여 눈을 건조하게 해요.",

        "immune":       "* <span class='highlight_1'>자가면역질환</span>의 진행으로 눈 주변 염증 및 표면 손상되었을 수 있어요",        
        "circulation":   "* <span class='highlight_1'>고혈압 등 순환계 질환</span> 또는 <span class='highlight_1'>당뇨병</span> 등 혈액순환을 저해하는 질환은, 눈 주변 모세혈관의 혈액흐름을 방해하여 안구건조를 촉진해요.",
        "symnerve":     "* <span class='highlight_1'>교감신경이 항진</span>되거나 <span class='highlight_1'>스트레스가 누적</span>되면 눈물 생성이 줄어요.",
        "diabetes":      "* <span class='highlight_1'>고혈압 등 순환계 질환</span> 또는 <span class='highlight_1'>당뇨병</span> 등 혈액순환을 저해하는 질환은, 눈 주변 모세혈관의 혈액흐름을 방해하여 안구건조를 촉진해요.",
        
        "stress":       "* <span class='highlight_1'>교감신경이 항진</span>되거나 <span class='highlight_1'>스트레스가 누적</span>되면 눈물 생성이 줄어요.",
        "coffee":       "* <span class='highlight_1'>교감신경이 항진</span>되거나 <span class='highlight_1'>스트레스가 누적</span>되면 눈물 생성이 줄어요.",
        "sleep":        "* <span class='highlight_1'>수면 시간이 부족</span>하면 눈물 생성이 줄어요.",

        "isotretinoin" : "* 피지조절제로 복용하는 <span class='highlight_3'>이소트레티노인</span> 성분의 의약품은 마이봄샘의 지질 분비를 억제하여 눈을 건조하게 해요.",
        "antihistamine" : "* 항히스타민제는 눈물 생성을 감소시켜 눈을 건조하게 해요.",
        "antidepressant" : "* 일부 항우울제는 눈물 생성을 감소시켜 눈을 건조하게 해요.",        
        "digestive" :       "* 일부 위장약은 눈물 생성을 감소시켜 눈을 건조하게 해요.",        
        
        "tinnitus" :    "* 이명 또는 잦은 빈도의 두통은 교감신경 항진으로 인한 것일 수 있어요. * <span class='highlight_1'>교감신경이 항진</span>되거나 <span class='highlight_1'>스트레스가 누적</span>되면 눈물 생성이 줄어요.",
        "headache" :    "* 이명 또는 잦은 빈도의 두통은 교감신경 항진으로 인한 것일 수 있어요. * <span class='highlight_1'>교감신경이 항진</span>되거나 <span class='highlight_1'>스트레스가 누적</span>되면 눈물 생성이 줄어요."
    }

    solution_comments_dic = {
        "2h": "* 야간 모니터 사용을 줄여주세요. 스마트폰이나 윈도우에서 제공하는 <span class='highlight_1'>야간 모드나 다크 모드</span>를 사용해 보세요. * 눈의 긴장을 풀기 위해 <span class='highlight_1'>20분마다 6m(20피트) 이상 떨어져 있는 대상을 20초 정도 바라보는 '20-20-20 운동'</span> 을 추천해요.",

        "space": "* <span class='highlight_1'>가습기, 공기청정기 등 실내 공기 질 및 습도 개선을 위한 수단</span>을 활용해 보세요.",
        "weather": "* 미세먼지가 심하거나 바람이 심하게 부는 날에는, 눈을 보호할 수 있는 안경을 착용하시거나 야외에 있는 시간을 줄여주세요.",
        "aircon":       "* 바람을 직접 쐬지 않도록 해 주세요. 환경상 어렵다면 눈을 보호하기 위한 안경을 착용하셔도 좋아요. ",
        "getup" : "* <span class='highlight_1'>기상 후 눈 건조</span>가 심하면, <span class='highlight_1'>취침전 겔 형태의 점안제</span>를 사용하거나 <span class='highlight_1'>눈을 덮는 의료용 반창고</span>를 사용해볼 수 있어요.",        
        "cosmetics" : "* <span class='highlight_1'>눈 주변에 사용하는 화장품</span>이 원인일 수 있어요. 자극이 덜한 제품으로 바꾸거나, 눈과 멀리 하여 사용해 주세요.",

        "immune":  "* 기저질환이 잘 관리되면, 부수적으로 눈 건조 완화에 도움이 될 수 있어요.",
        "circulation":  "* 기저질환이 잘 관리되면, 부수적으로 눈 건조 완화에 도움이 될 수 있어요.",
        "diabetes" : "* 기저질환이 잘 관리되면, 부수적으로 눈 건조 완화에 도움이 될 수 있어요.",
        
        "symnerve": "* <span class='highlight_1'>교감신경 항진</span> 및 <span class='highlight_1'>누적된 스트레스</span>를 줄이기 위해 <span class='highlight_2'>마그네슘, 레시틴 등 영양제</span>를 섭취할 수 있어요.",
        
        "stress": "* <span class='highlight_1'>교감신경 항진</span> 및 <span class='highlight_1'>누적된 스트레스</span>를 줄이기 위해 <span class='highlight_2'>마그네슘, 레시틴 등 영양제</span>를 섭취할 수 있어요.",
        "tinnitus" : "* <span class='highlight_1'>교감신경 항진</span> 및 <span class='highlight_1'>누적된 스트레스</span>를 줄이기 위해 <span class='highlight_2'>마그네슘, 레시틴 등 영양제</span>를 섭취할 수 있어요.",
        "headache" : "* <span class='highlight_1'>교감신경 항진</span> 및 <span class='highlight_1'>누적된 스트레스</span>를 줄이기 위해 <span class='highlight_2'>마그네슘, 레시틴 등 영양제</span>를 섭취할 수 있어요.",
        "coffee" : "* <span class='highlight_1'>교감신경 항진</span> 및 <span class='highlight_1'>누적된 스트레스</span>를 줄이기 위해 <span class='highlight_2'>마그네슘, 레시틴 등 영양제</span>를 섭취할 수 있어요.",
        "sleep": "* <span class='highlight_1'>수면 시간</span>을 늘려주세요. 적정 수면 시간은 7~8시간이에요.",

        "isotretinoin" : "* <span class='highlight_3'>의약품 복용 중 눈 건조 부작용이 심할 경우 처방해주신 의사선생님과 복용량 및 복용 여부에 대해 상담</span>하세요. * <span class='highlight_3'>이소트레티노인 의약품을 복용하는 동안에는, 눈이 건조해도 비타민 A 영양제 섭취는 피하는 것</span>이 좋아요.",
        "antihistamine" : "* <span class='highlight_3'>의약품 복용 중 눈 건조 부작용이 심할 경우 처방해주신 의사선생님과 복용량 및 복용 여부에 대해 상담</span>하세요.",
        "antidepressant" : "* <span class='highlight_3'>의약품 복용 중 눈 건조 부작용이 심할 경우 처방해주신 의사선생님과 복용량 및 복용 여부에 대해 상담</span>하세요.",
        "digestive" : "* <span class='highlight_3'>의약품 복용 중 눈 건조 부작용이 심할 경우 처방해주신 의사선생님과 복용량 및 복용 여부에 대해 상담</span>하세요.",

        "lens" : "* 가급적 <span class='highlight_1'>렌즈보다는 안경</span>을 착용해주세요."
    }

    for value in answers_dict.values():
        # 값을 콤마로 분리하여 리스트 생성
        splitted_values = [v.strip() for v in value.split(',')]
        
        for condition in splitted_values:
            # 각 사전에 대해 조건이 일치하는지 확인하고 적절한 리스트에 추가
            if condition in cause_keyword_dic:
                cause_keywords += cause_keyword_dic[condition]
            if condition in cause_comments_dic:
                cause_comments += cause_comments_dic[condition]
            if condition in solution_comments_dic:
                solution_comments += solution_comments_dic[condition]

        if (answers_dict.get("3", "") != "No" or answers_dict.get("5", "") != "No") and "10" in answers_dict and answers_dict.get("10", "") != "None":       
            if answers_dict.get("6", "") != "notyet" :
                cause_keywords += "* 마이봄샘 오염"
                cause_comments += "* <span class='highlight_1'>눈꺼풀 세정</span>이 필요할 수 있어요."
                solution_comments += "* 아직 사용해보시지 않았다면, <span class='highlight_2'>블레파졸 / 오큐소프트 등 눈꺼풀 세정제</span>를 사용해 보세요. * 눈 건조감 개선에, <span class='highlight_2'> 오메가3 성분이 풍부한 등푸른 생선 </span> 또는 <span class='highlight_2'>오메가3 영양제</span> 섭취가 도움될 수 있어요."
            else : 
                cause_keywords += "* 마이봄샘 변성, 파괴, 막힘"
                cause_comments += "* <span class='highlight_1'>마이봄샘 변성, 파괴, 막힘</span>은 눈을 보호하는 지질층 형성을 어렵게 해요."
                solution_comments += "* 눈을 자주 깜빡여주시고, 렌즈를 착용한다면 <span class='highlight_1'>렌즈보다는 안경</span>을 착용해주세요. * 눈 건조감 개선에, <span class='highlight_2'> 오메가3 성분이 풍부한 등푸른 생선 </span> 또는 <span class='highlight_2'>오메가3 영양제</span> 섭취가 도움될 수 있어요. * 마이봄샘을 풀어주기 위해, <span class='highlight_2'>온열찜질</span>을 해볼 수 있어요."

        # for key in range(4, 8):
        # answers_dict에서 해당 키의 값을 가져오고, 결과가 비어 있지 않은지 확인
            # values = answers_dict.get(str(key), [])                    # 
            # if values == "Yes":
            #     if key == 5:            #         
            #     elif key == 6:
            #         cause_comments += "* <span class='highlight_1'>마이봄샘 변성, 파괴, 막힘</span>은 눈을 보호하는 지질층 형성을 어렵게 해요."
            #         solution_comments += "* 눈을 자주 깜빡여주시고, 렌즈를 착용한다면 <span class='highlight_1'>렌즈보다는 안경</span>을 착용해주세요. * 눈 건조감 개선에, <span class='highlight_2'> 오메가3 성분이 풍부한 등푸른 생선 </span> 또는 <span class='highlight_2'>오메가3 영양제</span> 섭취가 도움될 수 있어요. * 마이봄샘을 풀어주기 위해, <span class='highlight_2'>온열찜질</span>을 해볼 수 있어요."
            #     elif key == 7:
            #         solution_comments += "* 눈 건조감 개선에, <span class='highlight_2'> 오메가3 성분이 풍부한 등푸른 생선 </span> 또는 <span class='highlight_2'>오메가3 영양제</span> 섭취가 도움될 수 있어요. * 마이봄샘을 풀어주기 위해, <span class='highlight_2'>온열찜질</span>을 해볼 수 있어요."
                
    # 위 for구문 다 돌렸는데도 아무런 코멘트 추가가 없을 경우 코멘트
    # if cause_comments == "" :       
    #    cause_comments += "* 안구건조감이 없고 불편감도 적다고 응답해주셔서, 현재 응답으로는 추정하기 어려워요."
    # 위 for구문 다 돌렸는데도 아무런 코멘트 추가가 없을 경우 솔루션 // 노출되는 솔루션 카테고리 이름은 html에서 if 조건으로 변경
    if solution_comments == "* 눈이 마르는 느낌이 들기 전에, 미리 <span class='highlight_1'>인공눈물</span>을 사용해주세요." :
       solution_comments = solution_comments.replace("* 눈이 마르는 느낌이 들기 전에, 미리 <span class='highlight_1'>인공눈물</span>을 사용해주세요.", "")
       solution_comments += "* 혹시 눈이 마르는 느낌이 든다면, <span class='highlight_1'>인공눈물</span>을 미리 사용해주세요. * 모니터/스마트폰을 장시간 본다면, 중간중간 눈을 의식하여 깜빡여주세요. * 눈이 긴장된다면, <span class='highlight_1'>20분마다 6m(20피트) 이상 떨어져 있는 대상을 20초 정도 바라보는 '20-20-20 운동'</span> 을 추천해요. * "

    # * 단위로 스플릿 후 중복 제거 (list,set)
    cause_keywordss_list = list(set([item.strip() for item in cause_keywords.split('*') if item.strip()]))
    cause_comments_list = list(set([item.strip() for item in cause_comments.split('*') if item.strip()]))
    solution_comments_list = list(set([item.strip() for item in solution_comments.split('*') if item.strip()]))

    # print (cause_comments_list)
    return cause_keywordss_list, cause_comments_list, solution_comments_list


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

    avoid_vitaminA = False

    if answers_dict.get("10", "") == "isotretinoin" :
        avoid_vitaminA = True
        pack1 = pack1_dic[12]
        pack2 = pack2_dic[11]

    if not avoid_vitaminA : 
    # 팩 노출 우선순위 정하기 전처리
        pack_decide_values_list = []
        for value in answers_dict.values():
            # 값을 콤마로 분리하여 리스트 생성
            splitted_values = value.split(',')
            # 각 분리된 값이 조건과 일치하는지 확인
            for item in splitted_values:
                pack_decide_values_list.append(item.strip())  # 공백 제거 후 추가
        print(pack_decide_values_list)

    # evaporate_signal_list = ['sight', 'burning', 'soreness', 'swell']
    # 팩1 노출순위 정하기
        if answers_dict.get("3", "") != "No" or answers_dict.get("5", "") != "No" : 
            if "6" in answers_dict and answers_dict["6"] == "notyet":
                pack1 = pack1_dic[7]
            else :
                pack1 = pack1_dic[8]
        elif any(v in pack_decide_values_list for v in ["stress", "caffeine"]):
            pack1 = pack1_dic[2]
        elif "sleep" in pack_decide_values_list :
            pack1 = pack1_dic[5]
        else : 
            pack1 = pack1_dic[1]

        # 팩2 노출순위 정하기
        if tear_evaporate_score + tear_lack_score > 5 and "sleep" not in pack_decide_values_list :
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
