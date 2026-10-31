"""Constraint-based Editing Planner driven by real visual-model evidence and music."""
import hashlib
import json
import math
import numpy as np
from .profiles import PROFILES


def duplicate(a,b):
    h=sum(x!=y for x,y in zip(a['phash'],b['phash']))
    similarity=float(np.dot(a['embedding'],b['embedding']))
    colour=float(np.mean(np.abs(np.array(a['rgb_mean'])-b['rgb_mean'])))/255
    return (h<=5 and similarity>.97) or (similarity>.995 and colour<.06)


def phase_boundaries(duration,climax):
    opening=round(duration*.17*30)/30
    climax_start=round(max(duration*.45,min(climax-duration*.10,duration*.72))*30)/30
    climax_end=round(min(duration*.87,max(climax+duration*.13,climax_start+1))*30)/30
    return [0.,opening,climax_start,climax_end,float(duration)]


def phase_at(time,duration,climax):
    boundaries=phase_boundaries(duration,climax)
    for index,name in enumerate(('opening','development','climax','ending')):
        if time<boundaries[index+1]-.001:return name
    return 'ending'


def build_timeline(candidates,metas,music,duration,style='cinematic',variant=0,allow_ramp=True):
    profile=PROFILES[style]
    pool=[c for c in candidates if not c['rejected'] and c['available']>=1.2]
    if not pool: raise ValueError('Không có cảnh đạt chất lượng. Xem báo cáo phân tích hoặc thêm footage.')
    selected=[];discarded=[]
    # Higher-quality near-duplicates win. No uniform random cuts or placeholder AI.
    for c in sorted(pool,key=lambda c:c['quality_score'],reverse=True):
        if any(duplicate(c,s) for s in selected): discarded.append([c['source'],c['start']]);continue
        selected.append(c)
    capacity=sum(max(0,c['available']-.45) for c in selected)
    if capacity<duration:
        raise ValueError(f'Chỉ có khoảng {capacity:.1f} giây cảnh khác biệt đạt chất lượng, chưa đủ {duration} giây. Hãy thêm video.')
    shots=[];used=set();elapsed=0.
    beats=music['beats']
    while elapsed<duration-.01:
        stage=phase_at(elapsed,duration,music['climax'])
        boundaries=phase_boundaries(duration,music['climax'])
        phase_end=next(boundary for boundary in boundaries[1:] if boundary>elapsed+.001)
        last=shots[-1] if shots else None
        scored=[]
        for c in selected:
            key=(c['source'],c['start'])
            if key in used: continue
            score=.60*c['quality_score']+.10*c['composition']+.10*c['aesthetic_proxy']
            landscape=max(c['scene_scores'].get('coast',0),c['scene_scores'].get('nature',0),c['scene_scores'].get('architecture',0))
            if stage=='opening': score+=.35*landscape+.12*(1-min(1,c['motion']/.04))
            elif stage=='development': score+=.25*c['scene_scores'].get('people',0)+.08*(c['tag'] in ('food','transport','interior'))
            elif stage=='climax': score+=.20*min(1,c['motion']/.035)+.12*c['semantic_confidence']
            else: score+=.25*landscape+.20*(1-min(1,c['motion']/.04))
            if last:
                score+=.09*(c['source']!=last['source'])+.08*(c['tag']!=last['tag'])
                # Avoid incoherent jumps within a source while still allowing intentional cuts.
                if c['source']==last['source'] and c['start']<last['start']: score-=.07
            scored.append((score,c))
        if not scored: raise ValueError('Hết cảnh không lặp trước khi đủ thời lượng. Hãy thêm nguồn.')
        scored.sort(key=lambda pair:(-pair[0],pair[1]['source'],pair[1]['start']))
        alternatives=[pair for pair in scored[:4] if scored[0][0]-pair[0]<=.12]
        choice=variant%len(alternatives)
        score,c=alternatives[choice]
        max_length=min(c['available']-.3,duration-elapsed,phase_end-elapsed)
        target=profile['shot_seconds']*(.78 if stage=='climax' else 1.03 if stage=='ending' else 1)
        target=min(target,max_length)
        future_phases=3-('opening','development','climax','ending').index(stage)
        if len(scored)<=future_phases+1: target=max_length
        target=min(max(target,.75),max_length)
        # Avoid an unusably short final tail.
        if 0<=phase_end-elapsed-target<.7 and phase_end-elapsed<=max_length+.001: target=phase_end-elapsed
        near=[b for b in beats if elapsed+.75<=b<=elapsed+max_length and abs(b-(elapsed+target))<.65]
        end=min(near,key=lambda b:abs(b-(elapsed+target))) if near and elapsed+target<phase_end-.7 else elapsed+target
        end=round(min(duration,end)*30)/30
        length=min(duration-elapsed,end-elapsed)
        if length<.05: used.add((c['source'],c['start']));continue
        use_ramp=bool(allow_ramp and profile['ramp'] and stage=='climax' and c['motion']>.008 and c['shake']<.025 and length>=1.2 and length+.3<=c['available'])
        # A dissolve is a tail handle; next shot's visible start stays on the planned beat.
        transition=min(profile['transition'],max(0,c['available']-length-(.3 if use_ramp else 0)),length*.2)
        reason={'opening':'Ưu tiên cảnh rộng/kiến trúc và chuyển động ổn định',
                'development':'Ưu tiên con người, chi tiết và đa dạng nguồn',
                'climax':'Ưu tiên chuyển động ở đoạn nhạc nhiều năng lượng',
                'ending':'Ưu tiên cảnh êm, phong cảnh và nhịp kết chậm'}[stage]
        shots.append({**c,'timeline':round(elapsed,6),'length':round(length,6),'phase':stage,
                      'ramp':use_ramp,'transition':round(transition,6),'selection_score':round(score,5),
                      'reason':reason,'beat_aligned':bool(any(abs(elapsed-b)<.05 for b in beats))})
        used.add((c['source'],c['start']));elapsed+=length
    for index,shot in enumerate(shots[:-1]):
        shot['transition']=math.floor(min(shot['transition'],shots[index+1]['length']*.25)*30)/30
    shots[-1]['transition']=0.
    # Short edits/shot lengths may skip a phase boundary; identify explicitly rather than invent shots.
    fingerprint=hashlib.sha256(json.dumps([(s['source'],s['start'],s['length']) for s in shots]).encode()).hexdigest()
    return {'version':1,'method':'constraint-based planner using local neural visual features',
            'style':style,'variant':variant,'duration':duration,'timeline':shots,'discarded_duplicates':discarded,
            'chapters':[{'name':p,'start':min(s['timeline'] for s in shots if s['phase']==p)} for p in ('opening','development','climax','ending') if any(s['phase']==p for s in shots)],
            'fingerprint':fingerprint,'warnings':['Bố cục/thẩm mỹ và chất lượng dùng proxy đo ảnh; không có mô hình thẩm mỹ hay LLM kể chuyện.',
            'Nhãn phong cảnh từ ImageNet là giới hạn; người/đồ vật từ COCO. Không nhận diện danh tính hoặc POV đáng tin cậy.']}
