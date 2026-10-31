"""FFmpeg H.264 renderer: measured colour matching, subject anchor, bounded joins."""
from pathlib import Path
import math
import numpy as np
from .engine import ff,probe,run
from .profiles import PROFILES


def colour_grades(shots):
    by_source={}
    for s in shots: by_source.setdefault(s['source'],[]).append(s['rgb_mean'])
    medians={key:np.median(values,axis=0) for key,values in by_source.items()}
    target=np.median(list(medians.values()),axis=0)
    result={}
    for source,rgb in medians.items():
        ratio=target/np.maximum(rgb,10)
        gains=np.clip(ratio/max(float(np.mean(ratio)),1e-6),.94,1.06)
        brightness=float(np.clip((np.mean(target)-np.mean(rgb))/255,-.035,.035))
        result[source]={'gains':gains.tolist(),'brightness':brightness,'method':'conservative statistical RGB matching, SDR'}
    return result


def encode_args():
    return ['-map_metadata','-1','-map_chapters','-1','-c:v','libx264','-preset','fast','-crf','18','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000']


def join_group(items,target):
    if len(items)==1: return items[0]
    args=[];filters=[]
    for i,item in enumerate(items):
        args+=['-i',item['path']]
        filters+=[f'[{i}:v]setpts=PTS-STARTPTS,fps=30,settb=1/30,format=yuv420p[v{i}]',f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]']
    v,a='v0','a0';elapsed=items[0]['core']
    for i in range(1,len(items)):
        d=items[i-1]['tail'];nv,na=f'jv{i}',f'ja{i}'
        if d>=1/30-.00001:
            filters+=[f'[{v}][v{i}]xfade=transition=fade:duration={d:.8f}:offset={elapsed:.8f},fps=30,settb=1/30[{nv}]',f'[{a}][a{i}]acrossfade=d={d:.8f}:c1=tri:c2=tri[{na}]']
        else:
            filters+=[f'[{v}][{a}][v{i}][a{i}]concat=n=2:v=1:a=1[raw{nv}][{na}]',f'[raw{nv}]fps=30,settb=1/30[{nv}]']
        v,a=nv,na;elapsed+=items[i]['core']
    ff(*args,'-filter_complex',';'.join(filters),'-map',f'[{v}]','-map',f'[{a}]',
       '-t',elapsed+items[-1]['tail'],'-r',30,*encode_args(),target)
    return {'path':target,'core':elapsed,'tail':items[-1]['tail']}


def render_timeline(videos,metas,music,timeline,folder,width,height,nature,update):
    folder=Path(folder);shots=timeline['timeline'];profile=PROFILES[timeline['style']]
    grades=colour_grades(shots);items=[];temporary=[]
    for i,s in enumerate(shots):
        update(48+int(i/max(1,len(shots))*30),f'Dựng cảnh {i+1}/{len(shots)} · {s["phase"]}')
        length=s['length']+s['transition'];extra=.3 if s['ramp'] else 0
        args=['-ss',s['start'],'-t',length+extra,'-i',videos[s['source']]]
        audio='0:a'
        if not metas[s['source']]['audio']:
            args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo'];audio='1:a'
        mapping=f"if(lt(T,0.6),0.5*T+T*T/2.4,if(lt(T,{length-.3}),T-0.15,{length-.45}+(T-{length-.3})-(T-{length-.3})*(T-{length-.3})/2.4))"
        vf=(f"setpts='{mapping}/TB'," if s['ramp'] else 'setpts=PTS-STARTPTS,')
        ax,ay=[float(np.clip(value,0,1)) for value in s['anchor']]
        # Frame-global anchor; explicit bounding box evidence, no unsupported tracking claim.
        vf+=f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:x='max(0,min(iw-ow,iw*{ax}-ow/2))':y='max(0,min(ih-oh,ih*{ay}-oh/2))',setsar=1,fps=30"
        g=grades[s['source']];r,green,b=g['gains']
        vf+=f",colorchannelmixer=rr={r}:gg={green}:bb={b},eq=brightness={g['brightness']}:saturation={profile['saturation']}:contrast={profile['contrast']},format=yuv420p"
        af=f'[{audio}]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS'
        if s['ramp']:
            af+=f',asplit=3[aa][ab][ac];[aa]atrim=0:0.6,asetpts=PTS-STARTPTS,atempo=1.333333333[aa1];[ab]atrim=0.6:{length-.3},asetpts=PTS-STARTPTS[ab1];[ac]atrim=start={length-.3},asetpts=PTS-STARTPTS,atempo=1.333333333[ac1];[aa1][ab1][ac1]concat=n=3:v=0:a=1'
        af+=f',apad,atrim=duration={length},volume={profile["nature"] if nature else 0}[ao]'
        target=folder/f'ai-clip-{i:03}.mp4'
        ff(*args,'-vf',vf,'-filter_complex',af,'-map','0:v:0','-map','[ao]','-t',length,*encode_args(),target)
        items.append({'path':target,'core':s['length'],'tail':s['transition']});temporary.append(target)
    # At most four input decoders per join; scales to long edits without one huge filtergraph.
    level=0
    while len(items)>1:
        update(80+min(level*2,7),'Ghép chuyển cảnh và hòa âm')
        joined=[]
        for group_index,start in enumerate(range(0,len(items),4)):
            group=items[start:start+4]
            target=folder/f'join-{level}-{group_index}.mp4'
            item=join_group(group,target);joined.append(item)
            if len(group)>1:
                temporary.append(target)
                for old in group:
                    if old['path'].exists():old['path'].unlink()
        items=joined;level+=1
    duration=timeline['duration'];update(90,'Trộn nhạc và kiểm tra MP4')
    # Apply fades once globally, after joins. No loop: selected music excerpt is long enough.
    mix=f'[0:a]afade=t=in:d=0.6,afade=t=out:st={duration-1}:d=1[a];[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=.65,afade=t=in:d=1,afade=t=out:st={duration-1.5}:d=1.5[m];[a][m]amix=inputs=2:normalize=0:duration=first,alimiter=limit=.94[out]'
    vf=f'fade=t=in:d=0.5,fade=t=out:st={duration-.7}:d=0.7,format=yuv420p'
    ff('-i',items[0]['path'],'-ss',music['start'],'-i',music['path'],'-vf',vf,'-filter_complex',mix,'-map','0:v:0','-map','[out]','-t',duration,*encode_args(),'-movflags','+faststart','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',folder/'result.mp4')
    actual=probe(folder/'result.mp4')
    if not actual['audio'] or actual['video']['width']!=width or actual['video']['height']!=height or actual['video']['codec_name']!='h264' or actual['video']['r_frame_rate']!='30/1' or abs(actual['duration']-duration)>.25:
        raise ValueError('Bản xuất không đạt kiểm tra codec, kích thước, âm thanh hoặc thời lượng.')
    # Decode entire result (both streams) to detect truncated packets/codec errors.
    run(['ffmpeg','-v','error','-xerror','-threads','2','-i',str(folder/'result.mp4'),'-map','0:v:0','-map','0:a:0','-f','null','-'])
    from .validation import content_metrics
    metrics=content_metrics(folder/'result.mp4',duration)
    update(98,'Video đã giải mã kiểm chứng toàn bộ hình và âm thanh')
    for path in temporary:
        path.unlink(missing_ok=True)
    return {'codec':'h264','width':width,'height':height,'fps':30,'audio':'aac','duration':actual['duration'],'fully_decoded':True,'colour_grades':grades,**metrics}
