"""End-to-end local AI pipeline with reusable analysis and inspectable evidence."""
import hashlib
import json
from pathlib import Path
from .vision import get_vision
from .analysis import analyze_video
from .music import analyze_music
from .planner import build_timeline
from .rendering import render_timeline
from .profiles import dimensions


def write_json(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)


def signature(paths,vision):
    # Immutable job files; size/mtime detect changes when used via the local CLI.
    return hashlib.sha256(json.dumps({'version':1,'sources':[(str(p.resolve()),p.stat().st_size,p.stat().st_mtime_ns) for p in paths],
                                      'weights':vision.fingerprints}).encode()).hexdigest()


def render_ai(videos,music,folder,duration=36,style='cinematic',resolution='1080p',aspect='9:16',variant=0,ramp=True,nature=True,update=lambda *args:None,cache_folder=None,test_size=None):
    if not music: raise ValueError('Chế độ AI cần bản nhạc của bạn. Hãy tải nhạc lên.')
    videos=[Path(p) for p in videos];music=Path(music);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    update(2,'Nạp mô hình AI cục bộ')
    vision=get_vision();key=signature(videos,vision)
    cached=Path(cache_folder or folder)/'analysis.json';data=None
    if cached.exists():
        try:
            existing=json.loads(cached.read_text(encoding='utf-8'))
            if existing.get('cache_key')==key:data=existing
        except (ValueError,OSError):pass
    reused=data is not None
    if data is None:
        metas=[];candidates=[]
        for i,p in enumerate(videos):
            update(5+int(i/len(videos)*33),f'AI phân tích video {i+1}/{len(videos)}')
            meta,found=analyze_video(p,i,vision,lambda ratio: update(5+int((i+ratio)/len(videos)*33),f'AI video {i+1}/{len(videos)} · {int(ratio*100)}%'))
            metas.append(meta);candidates.extend(found)
        data={'cache_key':key,'metas':metas,'candidates':candidates,'models':vision.fingerprints,'analysis_fps':8,'semantic_samples_per_window':3}
        write_json(cached,data)
    if cached.parent!=folder: write_json(folder/'analysis.json',data)
    if sum(m['duration'] for m in data['metas'])<duration: raise ValueError('Tổng footage chưa đủ thời lượng yêu cầu. Hãy thêm video.')
    update(40,'Phân tích nhịp, năng lượng và chọn đoạn nhạc')
    music_data=analyze_music(music,duration)
    write_json(folder/'music.json',music_data)
    update(44,'AI Editing Planner tạo bố cục câu chuyện bốn phần')
    timeline=build_timeline(data['candidates'],data['metas'],music_data,duration,style,variant,ramp)
    write_json(folder/'timeline.json',timeline)
    width,height=dimensions(resolution,aspect)
    if test_size is not None: width,height=test_size # Internal tests only; not exposed by API.
    output=render_timeline(videos,data['metas'],{**music_data,'path':music},timeline,folder,width,height,nature,update)
    report={'mode':'local-ai','backend':'PyTorch CPU','models':data['models'],'analysis_reused':reused,
            'style':style,'variant':variant,'candidate_count':len(data['candidates']),
            'rejected_quality':sum(c['rejected'] for c in data['candidates']),
            'discarded_duplicates':len(timeline['discarded_duplicates']),'selected':timeline['timeline'],
            'chapters':timeline['chapters'],'fingerprint':timeline['fingerprint'],'music':music_data,
            'output':output,'warnings':timeline['warnings']+music_data['warnings'],
            'privacy':{'third_party_media_upload':False,'external_ai_api_calls':0},
            'limitations':['Nhận diện theo mẫu ba khung hình/cửa sổ; có thể bỏ sót chủ thể thoáng qua.',
            'Optical flow lấy mẫu 8 FPS chỉ ước lượng rung; chưa có chống rung.',
            'Cân màu thống kê SDR, chưa có D-Log/HDR hoặc mô hình colorist.',
            'Crop neo người theo vị trí trung vị, không bám chủ thể theo thời gian.',
            'Không có mô hình thẩm mỹ được huấn luyện hoặc LLM viết câu chuyện ngữ nghĩa.']}
    write_json(folder/'report.json',report)
    return report
