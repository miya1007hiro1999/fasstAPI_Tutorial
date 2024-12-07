from fastapi import FastAPI , Depends, HTTPException #new
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from starlette.templating import Jinja2Templates #new
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED

import db
from models import User, Task

import hashlib

app = FastAPI (
    title = 'FastAPIで作るtoDoアプリケーション',
    description='FastAPIチュートリアル：FastAPI（とstarlette）でシンプルなtoDoアプリを作ろう',
    version='0.9 beta'
)

security = HTTPBasic() 

#new テンプレート関連の設定（jinja2）
templates = Jinja2Templates(directory="templates")
jinja_env = templates.env  
# Jinja2.Environment : filterやglobalの設定用

def index(request:Request):
    return  templates.TemplateResponse('index.html',{ 'request': request})

def admin(request:Request, credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = hashlib.md5(credentials.password.encode()).hexdigest()
    
    #ユーザーとタスクを取得
    # とりあえず今はadminユーザのみ取得
    user = db.session.query(User).filter(User.username == username).first()
    task = db.session.query(Task).filter(Task.user_id == user.id).all() if user is not None else []
    db.session.close()

    if user is None or user.password != password:
        error = 'ユーザ名かパスワードが間違っています'
        raise HTTPException(
            status_code = HTTP_401_UNAUTHORIZED,
            detail = error,
            headers={"WWW-Authenticate":"Basic"}
        )

    return templates.TemplateResponse('admin.html',
                                    {'request': request,
                                    'user':user,
                                    'task':task})