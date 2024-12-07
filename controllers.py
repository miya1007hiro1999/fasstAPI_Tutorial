import db
from models import User, Task
from fastapi import FastAPI
from starlette.templating import Jinja2Templates #new
from starlette.requests import Request

app = FastAPI (
    title = 'FastAPIで作るtoDoアプリケーション',
    description='FastAPIチュートリアル：FastAPI（とstarlette）でシンプルなtoDoアプリを作ろう',
    version='0.9 beta'
)

#new テンプレート関連の設定（jinja2）
templates = Jinja2Templates(directory="templates")
jinja_env = templates.env  
# Jinja2.Environment : filterやglobalの設定用

def index(request:Request):
    return  templates.TemplateResponse('index.html',{ 'request': request})

def admin(request:Request):
    #ユーザーとタスクを取得
    # とりあえず今はadminユーザのみ取得
    user = db.session.query(User).filter(User.username == 'admin').first()
    task = db.session.query(Task).filter(Task.user_id == user.id).all()
    db.session.close()

    return templates.TemplateResponse('admin.html',
                                    {'request': request,
                                    'user':user,
                                    'task':task})