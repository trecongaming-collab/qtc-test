import json
import os
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .engine import render

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('QTC_DATA_DIR', ROOT.parent/'work'/'jobs')).resolve()
DATA.mkdir(parents=True,exist_ok=True)
@asynccontextmanager
async def lifespan(application):
    # Interrupted renders are explicitly marked, not left polling forever.
    for previous in DATA.glob('*/status.json'):
        try:
            record=json.loads(previous.read_text())
            if record['status'] in ('queued','running'):
                state(previous.parent,status='error',progress=0,message='Máy chủ đã khởi động lại; vui lòng dựng lại.')
        except (ValueError,KeyError):
            pass
    yield


app = FastAPI(title='QTC Travel Vlog', lifespan=lifespan)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
executor=ThreadPoolExecutor(max_workers=1)
slots=threading.BoundedSemaphore(3)
MAX_FILE=2*1024**3
MAX_TOTAL=10*1024**3


def state(folder, **values):
    temporary=folder/'status.tmp'
    temporary.write_text(json.dumps(values,ensure_ascii=False))
    temporary.replace(folder/'status.json')


def job_folder(job_id):
    try:
        if str(uuid.UUID(job_id))!=job_id: raise ValueError()
    except ValueError:
        raise HTTPException(404,'Không tìm thấy tác vụ')
    folder=DATA/job_id
    if not (folder/'status.json').exists(): raise HTTPException(404,'Không tìm thấy tác vụ')
    return folder




def worker(folder,videos,music,duration,ramp,nature):
    try:
        report=render(videos,music,folder,duration,ramp,nature,lambda p,m:state(folder,status='running',progress=p,message=m))
        state(folder,status='done',progress=100,message='Video đã sẵn sàng',summary={'scenes':len(report['selected']),'bpm':round(report['bpm'])})
    except Exception as e:
        (folder/'error.log').write_text(str(e))
        message=str(e) if isinstance(e,ValueError) else 'Không xử lý được media. Xem error.log trên máy chủ để chẩn đoán.'
        state(folder,status='error',progress=0,message=message)
    finally:
        slots.release()


@app.get('/')
def home(): return FileResponse(ROOT/'static'/'index.html')


@app.get('/api/health')
def health(): return {'ok':bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))}


@app.post('/api/jobs',status_code=202)
async def create(videos:list[UploadFile]=File(...),music:UploadFile|None=File(None),duration:int=Form(36),ramp:bool=Form(True),nature:bool=Form(True)):
    if duration not in range(30,46): raise HTTPException(422,'Thời lượng phải từ 30–45 giây')
    if not 1<=len(videos)<=20: raise HTTPException(422,'Chọn từ 1–20 video')
    if not slots.acquire(blocking=False): raise HTTPException(429,'Hàng đợi đầy. Vui lòng thử lại sau.')
    folder=DATA/str(uuid.uuid4()); folder.mkdir()
    paths=[]; total=0
    try:
        inputs=[*videos]+([music] if music and music.filename else [])
        for i,upload in enumerate(inputs):
            is_music=i>=len(videos)
            suffix=Path(upload.filename or '').suffix.lower()
            allowed={'.mp3','.wav','.m4a','.aac','.flac','.ogg'} if is_music else {'.mp4','.mov','.mkv','.m4v'}
            if suffix not in allowed: raise HTTPException(422,'Định dạng tệp không được hỗ trợ')
            path=folder/f'input{i:02}{suffix}'
            size=0
            with path.open('wb') as dest:
                while chunk:=await upload.read(1024*1024):
                    size+=len(chunk); total+=len(chunk)
                    if size>MAX_FILE or total>MAX_TOTAL: raise HTTPException(413,'Tối đa 2 GB/tệp và 10 GB/tác vụ')
                    dest.write(chunk)
            if not size: raise HTTPException(422,'Tệp rỗng')
            paths.append(path)
        state(folder,status='queued',progress=0,message='Đang chờ dựng')
        executor.submit(worker,folder,paths[:len(videos)],paths[-1] if len(paths)>len(videos) else None,duration,ramp,nature)
    except BaseException:
        slots.release(); shutil.rmtree(folder,ignore_errors=True); raise
    finally:
        for upload in [*videos]+([music] if music else []): await upload.close()
    return {'id':folder.name}


@app.get('/api/jobs/{job_id}')
def status(job_id:str): return json.loads((job_folder(job_id)/'status.json').read_text())


@app.get('/api/jobs/{job_id}/video')
def video(job_id:str,download:bool=False):
    folder=job_folder(job_id)
    if json.loads((folder/'status.json').read_text())['status']!='done': raise HTTPException(409,'Video chưa sẵn sàng')
    return FileResponse(folder/'result.mp4',media_type='video/mp4',filename='QTC-travel-vlog.mp4' if download else None)


@app.get('/api/jobs/{job_id}/report')
def report(job_id:str):
    folder=job_folder(job_id)
    if not (folder/'report.json').exists(): raise HTTPException(409,'Báo cáo chưa sẵn sàng')
    return FileResponse(folder/'report.json',media_type='application/json',filename='QTC-report.json')
