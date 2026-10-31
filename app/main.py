import json
import os
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from .engine import render
from .profiles import PROFILES, dimensions
from .vision import readiness

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('QTC_DATA_DIR',ROOT.parent/'work'/'jobs')).resolve()
DATA.mkdir(parents=True,exist_ok=True)
MAX_FILE=int(float(os.environ.get('QTC_MAX_FILE_GB','20'))*1024**3)
MAX_TOTAL=int(float(os.environ.get('QTC_MAX_TOTAL_GB','100'))*1024**3)
RESERVE=512*1024**2
executor=ThreadPoolExecutor(max_workers=1)
slots=threading.BoundedSemaphore(3)


class Settings(BaseModel):
    mode:Literal['ai','classic']='ai'
    duration:int=Field(default=36,ge=15,le=90)
    style:Literal['cinematic','luxury','energetic','relaxing','tiktok']='cinematic'
    resolution:Literal['1080p','4k']='1080p'
    aspect:Literal['9:16','16:9']='9:16'
    ramp:bool=True
    nature:bool=True
    variant:int=Field(default=0,ge=0,le=1000)


class Regenerate(BaseModel):
    style:Literal['cinematic','luxury','energetic','relaxing','tiktok']|None=None
    resolution:Literal['1080p','4k']|None=None
    aspect:Literal['9:16','16:9']|None=None


def write_json(path,values):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)


def state(folder,**values):write_json(folder/'status.json',values)


def job_folder(job_id):
    try:
        if str(uuid.UUID(job_id))!=job_id:raise ValueError()
    except ValueError:raise HTTPException(404,'Không tìm thấy tác vụ')
    folder=DATA/job_id
    if not (folder/'status.json').exists():raise HTTPException(404,'Không tìm thấy tác vụ')
    return folder


@asynccontextmanager
async def lifespan(application):
    for previous in DATA.glob('*/status.json'):
        try:
            record=json.loads(previous.read_text(encoding='utf-8'))
            if record['status'] in ('queued','running'):
                state(previous.parent,status='error',progress=0,message='Máy chủ đã khởi động lại; vui lòng dựng lại.')
        except (ValueError,KeyError):pass
    yield


app=FastAPI(title='QTC AI VIDEO EDITOR',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')


@app.middleware('http')
async def body_limit(request,call_next):
    length=request.headers.get('content-length')
    if length:
        try:too_large=int(length)>MAX_TOTAL+2*1024**2
        except ValueError:return JSONResponse({'detail':'Content-Length không hợp lệ'},400)
        if too_large:return JSONResponse({'detail':'Tổng upload vượt giới hạn cấu hình'},413)
    return await call_next(request)


def worker(folder,manifest,previous_id=None):
    try:
        settings=Settings(**manifest['settings'])
        origin=job_folder(manifest['origin_id'])
        videos=[origin/name for name in manifest['videos']]
        music=origin/manifest['music'] if manifest.get('music') else None
        update=lambda p,m:state(folder,status='running',progress=p,message=m)
        if settings.mode=='ai':
            from .ai_editor import render_ai
            report=render_ai(videos,music,folder,cache_folder=origin,update=update,
                             **settings.model_dump(exclude={'mode'}))
        else:
            width,height=dimensions(settings.resolution,settings.aspect)
            report=render(videos,music,folder,settings.duration,settings.ramp,settings.nature,update,width,height)
        same=False
        if previous_id and report.get('fingerprint'):
            old=DATA/previous_id/'report.json'
            if old.exists():
                same=json.loads(old.read_text(encoding='utf-8')).get('fingerprint')==report['fingerprint']
                if same:
                    report['warnings'].append('Chưa tạo được timeline khác với nguồn hiện có; hãy thêm footage hoặc đổi phong cách.')
                    write_json(folder/'report.json',report)
        message='Video đã sẵn sàng' if not same else 'Video sẵn sàng; timeline giống bản trước. Hãy đổi phong cách hoặc thêm footage.'
        selected=report.get('selected',[])
        state(folder,status='done',progress=100,message=message,summary={'scenes':len(selected),'mode':settings.mode,
              'variant':settings.variant,'style':settings.style,'chapters':report.get('chapters',[]),
              'different_from_previous':not same if previous_id else None,'warnings':report.get('warnings',[])})
    except Exception as e:
        (folder/'error.log').write_text(str(e),encoding='utf-8')
        message=str(e) if isinstance(e,ValueError) else 'Không xử lý được media. Xem error.log trong thư mục công việc hoặc WINDOWS.md.'
        state(folder,status='error',progress=0,message=message)
    finally:slots.release()


@app.get('/')
def home():return FileResponse(ROOT/'static'/'index.html')


@app.get('/api/health')
def health():return {'ok':bool(shutil.which('ffmpeg') and shutil.which('ffprobe')),'ai':readiness()}


@app.get('/api/config')
def config():
    return {'styles':PROFILES,'max_file_bytes':MAX_FILE,'max_total_bytes':MAX_TOTAL,
            'disk_free_bytes':shutil.disk_usage(DATA).free,'ai':readiness(),
            'resolutions':['1080p','4k'],'aspects':['9:16','16:9'],'min_ai_videos':5,'max_videos':20}


@app.post('/api/jobs',status_code=202)
async def create(videos:list[UploadFile]=File(...),music:UploadFile|None=File(None),duration:int=Form(36),
                 ramp:bool=Form(True),nature:bool=Form(True),mode:str=Form('ai'),style:str=Form('cinematic'),
                 resolution:str=Form('1080p'),aspect:str=Form('9:16')):
    try:settings=Settings(mode=mode,duration=duration,ramp=ramp,nature=nature,style=style,resolution=resolution,aspect=aspect)
    except ValidationError:raise HTTPException(422,'Phong cách, thời lượng (15–90 giây), chế độ hoặc cấu hình xuất không hợp lệ')
    minimum=5 if settings.mode=='ai' else 1
    if not minimum<=len(videos)<=20:raise HTTPException(422,f'Chọn {minimum}–20 video')
    if settings.mode=='ai':
        if not music or not music.filename:raise HTTPException(422,'Chế độ AI cần nhạc nền')
        if not readiness()['ready']:raise HTTPException(503,readiness()['message'])
    if settings.mode=='classic' and not 30<=duration<=45:raise HTTPException(422,'Chế độ classic hỗ trợ 30–45 giây')
    if not slots.acquire(blocking=False):raise HTTPException(429,'Hàng đợi đầy. Vui lòng thử lại sau.')
    folder=DATA/str(uuid.uuid4());total=0;paths=[]
    try:
        folder.mkdir()
        inputs=[*videos]+([music] if music and music.filename else [])
        for i,upload in enumerate(inputs):
            suffix=Path(upload.filename or '').suffix.lower()
            allowed={'.mp3','.wav','.m4a','.aac','.flac','.ogg'} if i>=len(videos) else {'.mp4','.mov','.mkv','.m4v'}
            if suffix not in allowed:raise HTTPException(422,'Định dạng tệp không được hỗ trợ')
            path=folder/f'input{i:02}{suffix}';size=0
            with path.open('wb') as dest:
                while chunk:=await upload.read(1024*1024):
                    size+=len(chunk);total+=len(chunk)
                    if size>MAX_FILE or total>MAX_TOTAL:raise HTTPException(413,'Dung lượng vượt giới hạn cấu hình của máy chủ')
                    if shutil.disk_usage(DATA).free<RESERVE+len(chunk):raise HTTPException(507,'Ổ đĩa không đủ dung lượng. Hãy dọn thư mục work hoặc chọn ổ khác.')
                    dest.write(chunk)
            if not size:raise HTTPException(422,'Tệp rỗng')
            paths.append(path.name)
        manifest={'origin_id':folder.name,'settings':settings.model_dump(),'videos':paths[:len(videos)],
                  'music':paths[-1] if len(paths)>len(videos) else None}
        write_json(folder/'request.json',manifest);state(folder,status='queued',progress=0,message='Đang chờ dựng')
        executor.submit(worker,folder,manifest)
    except BaseException:
        slots.release();shutil.rmtree(folder,ignore_errors=True);raise
    finally:
        for upload in [*videos]+([music] if music else []):await upload.close()
    return {'id':folder.name}


@app.post('/api/jobs/{job_id}/regenerate',status_code=202)
def regenerate(job_id:str,changes:Regenerate):
    parent=job_folder(job_id)
    if json.loads((parent/'status.json').read_text(encoding='utf-8'))['status']!='done':raise HTTPException(409,'Chờ bản dựng trước hoàn tất')
    if not (parent/'request.json').exists():raise HTTPException(409,'Tác vụ từ phiên bản cũ. Hãy tải lại nguồn một lần.')
    manifest=json.loads((parent/'request.json').read_text(encoding='utf-8'))
    values={**manifest['settings'],**changes.model_dump(exclude_none=True)}
    values['variant']+=1
    try:settings=Settings(**values)
    except ValidationError:raise HTTPException(422,'Số phiên bản vượt giới hạn; tạo tác vụ mới')
    if not slots.acquire(blocking=False):raise HTTPException(429,'Hàng đợi đầy')
    folder=DATA/str(uuid.uuid4())
    try:
        folder.mkdir();manifest['settings']=settings.model_dump()
        write_json(folder/'request.json',manifest);state(folder,status='queued',progress=0,message='Tạo phiên bản mới từ nguồn và phân tích đã lưu')
        executor.submit(worker,folder,manifest,job_id)
    except BaseException:
        slots.release();shutil.rmtree(folder,ignore_errors=True);raise
    return {'id':folder.name}


@app.get('/api/jobs/{job_id}')
def status(job_id:str):return json.loads((job_folder(job_id)/'status.json').read_text(encoding='utf-8'))


@app.get('/api/jobs/{job_id}/video')
def video(job_id:str,download:bool=False):
    folder=job_folder(job_id)
    if json.loads((folder/'status.json').read_text(encoding='utf-8'))['status']!='done':raise HTTPException(409,'Video chưa sẵn sàng')
    return FileResponse(folder/'result.mp4',media_type='video/mp4',filename='QTC-AI-video.mp4' if download else None)


@app.get('/api/jobs/{job_id}/report')
def report(job_id:str):
    folder=job_folder(job_id)
    if not (folder/'report.json').exists():raise HTTPException(409,'Báo cáo chưa sẵn sàng')
    return FileResponse(folder/'report.json',media_type='application/json',filename='QTC-analysis-report.json')


@app.get('/api/jobs/{job_id}/timeline')
def timeline(job_id:str):
    folder=job_folder(job_id)
    if not (folder/'timeline.json').exists():raise HTTPException(409,'Timeline AI chưa sẵn sàng')
    return FileResponse(folder/'timeline.json',media_type='application/json',filename='QTC-timeline.json')
