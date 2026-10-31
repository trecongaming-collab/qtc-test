"""Local, deterministic highlight selection and FFmpeg rendering. No external AI."""
import json
import math
import subprocess
import wave
from pathlib import Path

import numpy as np


def run(args, timeout=1800):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace')[-2500:])
    return p.stdout


def ff(*args):
    return run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-threads', '2', '-filter_threads', '1', '-filter_complex_threads', '1', *map(str, args)])


def probe(path):
    info = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], 60))
    video = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    duration = float(info.get('format', {}).get('duration', 0))
    if not math.isfinite(duration) or duration <= 0 or duration > 7200:
        raise ValueError('Tệp cần có thời lượng hợp lệ, tối đa 2 giờ.')
    return dict(duration=duration, video=video, audio=any(s['codec_type'] == 'audio' for s in info['streams']))


def analyze(path, index):
    meta = probe(path)
    if not meta['video']:
        raise ValueError('Không tìm thấy luồng video.')
    # Stream ALL decoded footage at 2 fps; bounded memory even for long inputs.
    cmd = ['ffmpeg', '-v', 'error', '-threads', '2', '-filter_threads', '1', '-i', str(path), '-an', '-vf', 'fps=2,scale=96:54', '-pix_fmt', 'gray', '-f', 'rawvideo', 'pipe:1']
    candidates, window, previous = [], [], None
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        try:
            frame_id = 0
            while True:
                data = process.stdout.read(96 * 54)
                if len(data) != 96 * 54:
                    break
                g = np.frombuffer(data, np.uint8).reshape(54, 96).astype(np.float32)
                lap = -4*g[1:-1,1:-1]+g[:-2,1:-1]+g[2:,1:-1]+g[1:-1,:-2]+g[1:-1,2:]
                sharp = float(np.var(lap))
                exposure = float(np.mean((g > 12) & (g < 245)))
                motion = float(np.mean(np.abs(g-previous))) if previous is not None else 0
                score = math.log1p(sharp)*exposure - max(0, motion-15)*0.1
                window.append((score, sharp, exposure, motion, g[::6,::8].flatten()/255))
                if len(window) == 8:
                    candidates.append(dict(source=index, start=(frame_id-7)/2, score=float(np.mean([v[0] for v in window])), sharp=float(np.mean([v[1] for v in window])), exposure=float(np.mean([v[2] for v in window])), motion=float(np.mean([v[3] for v in window])), signature=np.mean([v[4] for v in window], axis=0).tolist()))
                    window = []
                previous = g
                frame_id += 1
            if process.wait(timeout=30):
                raise RuntimeError('Giải mã video thất bại.')
        finally:
            if process.poll() is None:
                process.kill()
    if not candidates and meta['duration'] >= 1:
        candidates = [dict(source=index, start=0., score=0., sharp=0., exposure=1., motion=0., signature=[0.]*108)]
    return meta, candidates


def music_grid(music, folder, duration):
    """Energy-onset tempo estimate (60–150 BPM), not musical beat AI."""
    if not music:
        return 100., 0., 'Nhạc ambient tổng hợp nội bộ, nhịp 100 BPM.'
    raw = ff('-i', music, '-t', duration, '-vn', '-ac', 1, '-ar', 8000, '-f', 'f32le', 'pipe:1')
    samples = np.frombuffer(raw, np.float32)
    count = len(samples)//160
    if count < 100:
        return 100., 0., 'Nhạc quá ngắn: dùng lưới 100 BPM dự phòng.'
    energy = np.sqrt(np.mean(samples[:count*160].reshape(count,160)**2, axis=1))
    onset = np.maximum(0, np.diff(energy, prepend=energy[0]))
    if onset.max() < .0001:
        return 100., 0., 'Không tìm thấy nhịp rõ: dùng lưới 100 BPM dự phòng.'
    lags = range(20,51)
    lag = max(lags, key=lambda k: float(np.dot(onset[k:],onset[:-k])))
    phase = max(range(lag), key=lambda p: float(np.sum(onset[p::lag])))
    return 3000/lag, phase*.02, 'Nhịp ước lượng theo năng lượng âm thanh; có thể lệch với nhạc phức tạp.'


def ambient(path, duration):
    rate = 44100
    t = np.arange(int(rate*duration))/rate
    signal = np.zeros_like(t)
    for frequency in [130.81,164.81,196.,261.63,329.63,392.]:
        signal += .025*np.sin(2*np.pi*frequency*t)*(0.65+0.35*np.sin(2*np.pi*.08*t))
    beat = np.mod(t,.6)
    signal += .08*np.sin(2*np.pi*(65*beat-20*beat**2))*np.exp(-beat*18)
    signal *= np.minimum(1,t/2)*np.minimum(1,(duration-t)/3)
    stereo = np.column_stack([signal, signal*.94])
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((np.clip(stereo,-1,1)*32767).astype('<i2').tobytes())


def plan(candidates, metas, duration, bpm, phase):
    valid = [c for c in candidates if c['exposure'] > .5 and c['sharp'] > 6 and c['motion'] < 55]
    if not valid:
        raise ValueError('Không đủ cảnh đạt ngưỡng nét/phơi sáng. Hãy thử video khác.')
    ranked = sorted(valid, key=lambda c:c['score'], reverse=True)
    chosen = []
    # Opener is highest technical quality, followed by source diversity; no semantic claims.
    for c in ranked:
        if all(np.mean(np.abs(np.array(c['signature'])-np.array(v['signature']))) > .035 for v in chosen):
            chosen.append(c)
            if len(chosen) >= 60:
                break  # Bound pairwise comparisons; 60 unique windows exceed a 45s edit.
    pool = chosen[:1]
    remaining = chosen[1:]
    while remaining:
        last = pool[-1]['source']
        pick = next((c for c in remaining if c['source'] != last), remaining[0])
        pool.append(pick); remaining.remove(pick)
    shots, elapsed, used = [], 0., set()
    beat = 60/bpm
    while elapsed < duration-.001:
        available = [c for c in pool if (c['source'],c['start']) not in used]
        if not available:
            raise ValueError('Không đủ cảnh khác biệt để dựng 30–45 giây mà không lặp. Hãy thêm video.')
        c = available[0]
        target = min(duration, (round((elapsed+3.5-phase)/beat)*beat+phase))
        length = round(target-elapsed, 6)
        # Candidates cover 4 seconds. Ramp consumes an additional 0.3 seconds.
        length = min(length, 3.7, metas[c['source']]['duration']-c['start']-.3)
        if length < .05:
            used.add((c['source'],c['start'])); continue
        # Keep actual boundaries on beat when possible.
        if elapsed+length < duration-.01:
            boundary = math.floor((elapsed+length-phase)/beat)*beat+phase
            if boundary > elapsed+.5:
                length = boundary-elapsed
        shots.append({**c, 'length':length, 'timeline':elapsed, 'ramp':len(shots)%3==1})
        used.add((c['source'],c['start']))
        elapsed += length
    return shots


def render(videos, music, folder, duration, ramp, nature, update, width=1080, height=1920):
    folder = Path(folder)
    metas, candidates = [], []
    for i,path in enumerate(videos):
        update(5+int(i/len(videos)*25), f'Phân tích toàn thời lượng video {i+1}/{len(videos)} ở 2 khung hình/giây')
        meta, found = analyze(path,i); metas.append(meta); candidates.extend(found)
    total_duration = sum(meta['duration'] for meta in metas)
    if total_duration < duration:
        raise ValueError(f'Tổng video chỉ {total_duration:.2f} giây, chưa đủ dựng {duration} giây. Hãy thêm video.')
    bpm, phase, note = music_grid(music,folder,duration)
    shots = plan(candidates,metas,duration,bpm,phase)
    for shot in shots:
        shot['ramp'] = bool(ramp and shot['ramp'] and shot['length'] >= 1.2)
    if not music:
        music = folder/'ambient.wav'; ambient(music,duration)
    report = dict(method='Heuristic, không dùng AI ngữ nghĩa', bpm=bpm, beat_phase=phase, music_note=note, analysis_fps=2, candidates=len(candidates), selected=shots, warnings=['Cắt dọc giữa khung hình; chưa theo dõi chủ thể.', 'Độ rung chỉ ước lượng qua sai khác khung hình; không phải chống rung.', 'Màu SDR cố định; chưa có chuyển đổi HDR/D-Log chuyên biệt.'])
    (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    for i,shot in enumerate(shots):
        update(32+int(i/len(shots)*53),f'Dựng cảnh {i+1}/{len(shots)}')
        length=shot['length']; use_ramp=shot['ramp']
        extra=.3 if use_ramp else 0
        args=['-ss',shot['start'],'-t',length+extra,'-i',videos[shot['source']]]
        if not metas[shot['source']]['audio']:
            args += ['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
        # Smooth 2x → 1x → 2x video ramp; audio handles use average speed.
        mapping=f"if(lt(T,0.6),0.5*T+T*T/2.4,if(lt(T,{length-.3}),T-0.15,{length-.45}+(T-{length-.3})-(T-{length-.3})*(T-{length-.3})/2.4))"
        vf = (f"setpts='{mapping}/TB'," if use_ramp else 'setpts=PTS-STARTPTS,')
        vf += f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps=30,eq=contrast=1.025:saturation=1.07:brightness=0.005,colorbalance=bs=0.018:gs=0.006,format=yuv420p'
        if i==0: vf+=',fade=t=in:d=0.5'
        if i==len(shots)-1: vf+=f',fade=t=out:st={max(0,length-.7)}:d=0.7'
        audio_input='0:a' if metas[shot['source']]['audio'] else '1:a'
        af=f'[{audio_input}]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS'
        if use_ramp:
            af+=f',asplit=3[a][b][c];[a]atrim=0:0.6,asetpts=PTS-STARTPTS,atempo=1.333333333[a1];[b]atrim=0.6:{length-.3},asetpts=PTS-STARTPTS[b1];[c]atrim=start={length-.3},asetpts=PTS-STARTPTS,atempo=1.333333333[c1];[a1][b1][c1]concat=n=3:v=0:a=1'
        af+=f',apad,atrim=duration={length},volume={.32 if nature else 0},afade=t=in:d=0.08,afade=t=out:st={max(0,length-.12)}:d=0.12[ao]'
        ff(*args,'-vf',vf,'-filter_complex',af,'-map','0:v:0','-map','[ao]','-t',length,'-c:v','libx264','-preset','fast','-crf','18','-threads','2','-c:a','aac','-ar','48000',folder/f'clip{i:03}.mp4')
    listing=folder/'concat.txt'
    listing.write_text(''.join(f"file 'clip{i:03}.mp4'\n" for i in range(len(shots))))
    ff('-f','concat','-safe',0,'-i',listing,'-c','copy',folder/'joined.mp4')
    update(90,'Trộn nhạc và xuất MP4')
    mix=f'[0:a]afade=t=in:d=0.5,afade=t=out:st={duration-1}:d=1[a];[1:a]aresample=48000,volume=0.55,afade=t=in:d=1.5,afade=t=out:st={duration-2}:d=2[m];[a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[out]'
    ff('-i',folder/'joined.mp4','-stream_loop',-1,'-i',music,'-filter_complex',mix,'-map','0:v:0','-map','[out]','-c:v','copy','-c:a','aac','-b:a','192k','-t',duration,'-movflags','+faststart',folder/'result.mp4')
    actual=probe(folder/'result.mp4')
    report['output']={'duration':actual['duration'],'width':actual['video']['width'],'height':actual['video']['height'],'fps':actual['video']['r_frame_rate'],'codec':actual['video']['codec_name']}
    (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    for p in folder.glob('clip*.mp4'): p.unlink()
    (folder/'joined.mp4').unlink()
    return report
