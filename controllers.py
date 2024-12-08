from fastapi import FastAPI , Depends, HTTPException #new
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import FastAPI ,Depends,Form

from starlette.templating import Jinja2Templates #new
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED
from starlette.responses import RedirectResponse

from mycalendar import MyCalendar
from datetime import datetime, timedelta

import db
from models import User, Task
from auth import auth


import hashlib

import re
pattern = re.compile(r'\w{4,20}')
pattern_pw = re.compile(r'\w{6,20}')
pattern_mail = re.compile(r'^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$')  # e-mailの正規表現

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
    username = auth(credentials)
    #Basic認証で受け取った情報
    username = credentials.username
    password = hashlib.md5(credentials.password.encode()).hexdigest()
    
    """ [new] 今日の日付と来週の日付"""
    today = datetime.now()
    next_w = today + timedelta(days=7)  # １週間後の日付

    #ユーザーとタスクを取得
    # データベースからユーザー名が一致するデータを取得
    user = db.session.query(User).filter(User.username == username).first()
    

    #該当ユーザーがいない場合
    if user is None or user.password != password:
        error = 'ユーザ名かパスワードが間違っています'
        raise HTTPException(
            status_code = HTTP_401_UNAUTHORIZED,
            detail = error,
            headers={"WWW-Authenticate":"Basic"},
        )
        
    task = db.session.query(Task).filter(Task.user_id == user.id).all() if user is not None else []
    
    
    """ [new] カレンダー関連 """
    # カレンダーをHTML形式で取得
    cal = MyCalendar(username,
                        {t.deadline.strftime('%Y%m%d'): t.done for t in task})  # 予定がある日付をキーとして渡す

    cal = cal.formatyear(today.year, 4)  # カレンダーをHTMLで取得

    # 直近のタスクだけでいいので、リストを書き換える
    task = [t for t in task if isinstance(t.deadline, datetime) and today <= t.deadline <= next_w]
    links = [t.deadline.strftime('/todo/'+username+'/%Y/%m/%d') for t in task if isinstance(t.deadline, datetime)]
    

    #特に問題がなければ管理者ページへ
    response =  templates.TemplateResponse('admin.html',
                                    {'request': request,
                                    'user':user,
                                    'task':task,
                                    'links': links,
                                    'calender':cal})
    db.session.close()
    
    return response
    

async def register(request: Request):
    if request.method == 'GET':
        return templates.TemplateResponse('register.html',
                                            {'request': request,
                                                'username': '',
                                                'error': []})

    if request.method == 'POST':
        #POSTデータ
        data = await request.form()
        username = data.get('username')
        password = data.get('password')
        password_tmp = data.get('password_tmp')
        mail = data.get('mail')

        #new 

        error =[]

        tmp_user = db.session.query(User).filter(User.username == username).first()

        if tmp_user is not None:
            error.append('同じユーザー名のユーザーが存在します')
        if password != password_tmp:
            error.append('入力したパスワードが一致しません')
        if pattern.match(username) is None:
            error.append('ユーザー名は4~20文字の半角英数字にしてください')
        if pattern_pw.match(password) is None:
            error.append('パスワードは6~20文字の半角英数字にしてください')
        if pattern_mail.match(mail) is None:
            error.append('正しくメールアドレスを入力してください')


        if error:
            return templates.TemplateResponse('register.html',
                                                {'request':request,
                                                    'username' : username,
                                                    'error':error})         
        
        user = User(username,password,mail)
        db.session.add(user)
        db.session.commit()
        db.session.close()

        return templates.TemplateResponse('complete.html',
                                            {'request':request,
                                            'username':username})
                                            
def detail(request: Request, username,year,month,day, credentials: HTTPBasicCredentials = Depends(security)):
    
    username_tmp = auth(credentials)
    
    if username_tmp != username:
        return RedirectResponse('/')
    
    user = db.session.query(User).filter(User.username == username).first()
    
    task = db.session.query(Task).filter(Task.user_id == user.id).all()
    db.session.close()
    
    theday = '{}{}{}'.format(year, month.zfill(2),day.zfill(2))
    task = [t for t in task if t.deadline.strftime('%Y%m%d') == theday]
    
    return templates.TemplateResponse('detail.html',
                                        {'request':request,
                                        'username':username,
                                        'task':task,
                                        'year':year,
                                        'month':month,
                                        'day':day
                                        })          


async def done(request:Request,credentials:HTTPBasicCredentials = Depends(security)):
    username = auth(credentials)
    
    user = db.session.query(User).filter(User.username ==username).first()
    
    task = db.session.query(Task).filter(Task.user_id == user.id).all()
    
    data = await request.form()
    t_dones = data.getlist('done[]')
    
    for t in task:
        if str(t.id) in t_dones:
            t.done = True
            
    db.session.commit()
    db.session.close()
    
    return RedirectResponse('/admin')             

async def add(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    username = auth(credentials)
    
    user = db.session.query(User).filter(User.username == username).first()
    
    data = await request.form()
    year = int(data['year'])
    month = int(data['month'])
    day = int(data['day'])
    hour = int(data['hour'])
    minute = int(data['minute'])
    
    deadline = datetime(year=year, month=month,day=day,hour=hour,minute=minute)
    
    task = Task(user.id, data['content'],deadline)
    db.session.add(task)
    db.session.commit()
    db.session.close()
    
    return RedirectResponse('/admin')

def delete(request:Request, t_id, credentials: HTTPBasicCredentials = Depends(security)):
    username = auth(credentials)
    
    user = db.session.query(User).filter(User.username == username).first()
    
    task = db.session.query(Task).filter(Task.id == t_id).first()
    
    if task.user_id != user.id:
        return RedirectResponse('/admin')
    
    db.session.delete(task)
    db.session.commit()
    db.session.close()
    
    return RedirectResponse('/admin')

def get(request:Request, credentials: HTTPBasicCredentials = Depends(security)):
    username = auth(credentials)
    
    user = db.session.query(User).filter(User.username == username).first()
    
    task = db.session.query(Task).filter(Task.user_id == user.id).all()
    
    db.session.close()
    
    task = [{
        'id' : t.id,
        'content' :t.content,
        'deadline': t.deadline.strftime('%Y-%m-%d %H:%M:%S'),
        'published':t.date.strftime('%Y-%m-%d %H:%M:%S'),
        'done':t.done,
    } for t in task]
    
    return task    

async def insert(request:Request,
                 content: str = Form(...),deadline: str = Form(...),
                 credentials: HTTPBasicCredentials = Depends(security)):
    """
    タスクを追加してJSONで新規タスクを返す。「deadline」は%Y-%m-%d_%H:%M:%S (e.g. 2019-11-03_12:30:00)の形式
    """
    username = auth(credentials)
    
    user = db.session.query(User).filter(User.username == username).first()
    
    task = Task(user.id, content, datetime.strptime(deadline,'%Y-%m-%d_%H:%M:%S'))
    
    db.session.add(task)
    db.session.commit()
    
    task = db.session.query(Task).all()[-1]
    db.session.close()
    
    return{
        'id':task.id,
        'content':task.content,
        'deadline':task.deadline.strftime('%Y-%m-%d %H:%M:%S'),
        'published':task.date.strftime('%Y-%m-%d %H:%M:%S'),
        'done':task.done,
    }