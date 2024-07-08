from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import uvicorn
import json
import os

app = FastAPI()

# 현재 파일의 디렉토리 경로를 기준으로 templates 디렉토리 설정
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
print(f"Templates directory: {templates_dir}")  # 디버깅을 위해 추가
templates = Jinja2Templates(directory=templates_dir)

# 정적 파일 경로 설정
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit/{question_id}", response_class=HTMLResponse)
async def submit_answers(request: Request, question_id: int, answer: str = Form(...), existing_answers: Optional[str] = Form("")):
    if existing_answers:
        try:
            answers_dict = json.loads(existing_answers)
        except json.JSONDecodeError:
            answers_dict = {}
    else:
        answers_dict = {}

    answers_dict[str(question_id)] = answer  # question_id를 문자열로 변환하여 딕셔너리 키로 사용

    print(answers_dict)  # 디버깅을 위해 추가

    if question_id == 2 and "No" in answers_dict.values():
        next_question_id = 8  # "No"를 선택하면 question_id 8로 건너뜀
    elif question_id < 10:
        next_question_id = question_id + 1
    else:
        average_length = sum(len(a) for a in answers_dict.values()) / len(answers_dict)
        return templates.TemplateResponse("result.html", {"request": request, "answers": answers_dict, "score": average_length})

    updated_answers = json.dumps(answers_dict)
    return templates.TemplateResponse(f"question{next_question_id}.html", {"request": request, "question_id": next_question_id, "answers": updated_answers})

@app.get("/question/{question_id}", response_class=HTMLResponse)
async def get_question(request: Request, question_id: int, answers: Optional[str] = None):
    if question_id < 1 or question_id > 10:
        return templates.TemplateResponse("index.html", {"request": request})
    
    answers_dict = json.loads(answers) if answers else {}
    answers_json = json.dumps(answers_dict)
    
    return templates.TemplateResponse(f"question{question_id}.html", {"request": request, "question_id": question_id, "answers": answers_json})


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
