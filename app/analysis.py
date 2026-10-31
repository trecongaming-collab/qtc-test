"""8 fps quality/optical-flow scan; true local vision at three points/window."""
import math
import subprocess
import cv2
import numpy as np
from .engine import probe

FPS=8
SIDE=320
WINDOW=4


def quality(frames):
    grays=[cv2.cvtColor(f,cv2.COLOR_RGB2GRAY) for f in frames]
    sharp=[float(cv2.Laplacian(g,cv2.CV_32F).var()) for g in grays]
    exposure=[float(np.mean((g>12)&(g<244))) for g in grays]
    velocity=[];residual=[];tracked=[]
    for old,new in zip(grays[:-1],grays[1:]):
        points=cv2.goodFeaturesToTrack(old,maxCorners=90,qualityLevel=.02,minDistance=6)
        if points is None or len(points)<8: continue
        nxt,status,_=cv2.calcOpticalFlowPyrLK(old,new,points,None,winSize=(15,15),maxLevel=2)
        if nxt is None: continue
        good=status.ravel().astype(bool); a=points[good].reshape(-1,2);b=nxt[good].reshape(-1,2)
        if len(a)<8: continue
        matrix,inliers=cv2.estimateAffinePartial2D(a,b,method=cv2.RANSAC,ransacReprojThreshold=2.)
        if matrix is None: continue
        diag=math.hypot(*old.shape)
        velocity.append([float(matrix[0,2])/diag,float(matrix[1,2])/diag,math.atan2(matrix[1,0],matrix[0,0])])
        predicted=a@matrix[:,:2].T+matrix[:,2]
        residual.append(float(np.median(np.linalg.norm(b-predicted,axis=1)))/diag)
        tracked.append(len(a))
    v=np.array(velocity)
    motion=float(np.median(np.linalg.norm(v[:,:2],axis=1))) if len(v) else 0.
    shake=float(np.median(np.linalg.norm(np.diff(v,axis=0),axis=1))) if len(v)>2 else 0.
    flow_confidence=min(1,len(v)/max(1,len(grays)-1))*min(1,float(np.median(tracked))/35) if tracked else 0.
    sample=frames[len(frames)//2]
    hsv=cv2.cvtColor(sample,cv2.COLOR_RGB2HSV)
    gray=grays[len(grays)//2]
    edge=cv2.magnitude(cv2.Sobel(gray,cv2.CV_32F,1,0),cv2.Sobel(gray,cv2.CV_32F,0,1))
    # Edge-density balance and colour are composition/aesthetic proxies, NOT neural aesthetics.
    left=float(edge[:,:edge.shape[1]//2].sum());right=float(edge[:,edge.shape[1]//2:].sum())
    balance=1-abs(left-right)/max(1,left+right)
    colour=float(np.mean(hsv[:,:,1]))/255
    lighting=float(np.median(exposure))
    detail=float(np.median(sharp))
    technical=.40*min(1,math.log1p(detail)/7)+.35*lighting+.25*max(0,1-shake/.035)
    proxy=.65*balance+.35*min(1,colour/.55)
    small=cv2.resize(gray,(32,32)).astype(np.float32)
    dct=cv2.dct(small)[:8,:8]; bits=dct>np.median(dct[1:])
    phash=''.join(f'{int(b):01b}' for b in bits.ravel())
    return dict(sharp=detail,exposure=lighting,motion=motion,shake=shake,flow_confidence=flow_confidence,
                residual_flow=float(np.median(residual)) if residual else 0.,composition=balance,
                aesthetic_proxy=proxy,quality_score=technical,phash=phash,
                rgb_mean=np.mean([f.mean(axis=(0,1)) for f in frames],axis=0).tolist(),
                luminance=float(np.mean(gray))/255,
                rejected=detail<12 or lighting<.48 or (shake>.055 and flow_confidence>.4))


def summarize(frames,source,start,vision):
    measurements=quality(frames)
    indices=sorted(set([0,len(frames)//2,len(frames)-1]))
    semantics=[vision.infer(frames[i]) for i in indices]
    embedding=np.mean([s['embedding'] for s in semantics],axis=0)
    embedding/=max(float(np.linalg.norm(embedding)),1e-8)
    group_names=set().union(*(s['scene_scores'] for s in semantics))
    groups={k:float(np.mean([s['scene_scores'].get(k,0) for s in semantics])) for k in group_names}
    tag=max(groups,key=groups.get)
    if groups[tag]<.12: tag='unknown'
    objects=[{**o,'sample':i} for i,s in enumerate(semantics) for o in s['objects']]
    people=[o for o in objects if o['label']=='person']
    # Fixed crop anchor, not a tracking claim. Median detected person's centre when present.
    anchor=[float(np.median([(o['box'][0]+o['box'][2])/2 for o in people])),
            float(np.median([(o['box'][1]+o['box'][3])/2 for o in people]))] if people else [.5,.5]
    thirds=[(1/3,1/3),(1/3,2/3),(2/3,1/3),(2/3,2/3)]
    placement=1-min(math.hypot(anchor[0]-x,anchor[1]-y) for x,y in thirds)
    measurements['composition']=(measurements['composition']+placement)/2
    return dict(source=source,start=round(start,4),available=round(len(frames)/FPS,4),
                **measurements,tag=tag,scene_scores=groups,objects=objects,anchor=anchor,
                embedding=np.round(embedding,6).tolist(),labels=[s['labels'] for s in semantics],
                inference_samples=len(semantics),semantic_confidence=round(max(groups.values()),4),
                inference='pretrained-local',aesthetic_model=False)


def analyze_video(path,index,vision,progress=None):
    meta=probe(path)
    if not meta['video']: raise ValueError('Không có luồng video trong tệp nguồn.')
    video=meta['video']
    transfer=video.get('color_transfer','')
    if transfer in ('smpte2084','arib-std-b67'):
        raise ValueError('Nguồn HDR cần chuyển SDR trước. Bản này chưa có pipeline tone-map HDR đáng tin cậy.')
    width,height=video['width'],video['height']
    for side in video.get('side_data_list',[]):
        if abs(side.get('rotation',0))%180==90: width,height=height,width
    ratio=min(SIDE/width,SIDE/height)
    active_w,active_h=max(2,int(width*ratio)),max(2,int(height*ratio))
    x=(SIDE-active_w)//2;y=(SIDE-active_h)//2
    command=['ffmpeg','-v','error','-threads','2','-filter_threads','1','-i',str(path),'-map','0:v:0','-an','-vf',f'fps={FPS},scale={SIDE}:{SIDE}:force_original_aspect_ratio=decrease,pad={SIDE}:{SIDE}:(ow-iw)/2:(oh-ih)/2','-pix_fmt','rgb24','-f','rawvideo','pipe:1']
    candidates=[];frames=[];counter=0
    with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as process:
        try:
            while True:
                data=process.stdout.read(SIDE*SIDE*3)
                if not data: break
                if len(data)!=SIDE*SIDE*3: raise ValueError('Khung hình video bị cắt cụt khi giải mã.')
                frame=np.frombuffer(data,np.uint8).reshape(SIDE,SIDE,3)
                frames.append(frame[y:y+active_h,x:x+active_w].copy());counter+=1
                if len(frames)==FPS*WINDOW:
                    candidates.append(summarize(frames,index,(counter-len(frames))/FPS,vision))
                    if progress: progress(min(1,counter/FPS/meta['duration']))
                    frames=[]
            if len(frames)>=FPS*1.2:
                candidates.append(summarize(frames,index,(counter-len(frames))/FPS,vision))
            if process.wait(timeout=30): raise ValueError('Không giải mã được toàn bộ video.')
        finally:
            if process.poll() is None: process.kill()
    return meta,candidates
