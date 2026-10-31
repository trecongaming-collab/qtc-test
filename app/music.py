"""Full-track energy scan + spectral-flux beat tracking on the chosen excerpt."""
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks
from .engine import ff,probe


def analyze_music(path,duration):
    meta=probe(path)
    if not meta['audio']: raise ValueError('Nhạc không có luồng âm thanh.')
    if meta['duration']<duration: raise ValueError('Nhạc cần dài ít nhất bằng bản dựng; hãy chọn bản nhạc dài hơn.')
    if meta['duration']>1800: raise ValueError('Bản nhạc tối đa 30 phút; hãy cắt ngắn nhạc trước.')
    rate,hop=8000,160
    samples=np.frombuffer(ff('-i',path,'-vn','-ac',1,'-ar',rate,'-f','f32le','pipe:1'),np.float32)
    count=len(samples)//hop
    if count<1: raise ValueError('Không giải mã được nhạc.')
    rms=np.sqrt(np.mean(samples[:count*hop].reshape(-1,hop)**2,axis=1))
    if float(rms.max())<1e-5: raise ValueError('Bản nhạc im lặng, không thể dựng theo nhịp.')
    width=min(count,int(duration*rate/hop))
    cumulative=np.concatenate(([0.],np.cumsum(rms,dtype=np.float64)))
    energy=cumulative[width:]-cumulative[:-width]
    start_frame=int(np.argmax(energy)); start=start_frame*hop/rate
    # ffmpeg delay/rounding may shorten audio by a few milliseconds.
    start=min(start,max(0,meta['duration']-duration-.05))
    clip=samples[int(start*rate):int((start+duration)*rate)]
    frames=np.lib.stride_tricks.sliding_window_view(clip,512)[::hop]
    magnitude=np.abs(np.fft.rfft(frames*np.hanning(512),axis=1))
    flux=np.maximum(0,np.diff(magnitude,axis=0,prepend=magnitude[:1])).sum(axis=1)
    flux=np.maximum(0,flux-uniform_filter1d(flux,size=11))
    flux/=max(float(np.max(flux)),1e-8)
    peaks,_=find_peaks(flux,distance=10,prominence=.08)
    lags=np.arange(17,51) # approximately 60–176 BPM
    scores=np.array([np.dot(flux[k:],flux[:-k]) for k in lags])
    lag=int(lags[int(np.argmax(scores))])
    bpm=3000/lag
    phase=max(range(lag),key=lambda p:float(np.sum(flux[p::lag])))
    grid=np.arange(phase,len(flux),lag)
    beats=[]; support=[]
    for tick in grid:
        near=peaks[np.abs(peaks-tick)<=max(2,lag*.18)]
        if len(near):
            best=int(near[np.argmax(flux[near])]); beats.append(round((best*hop+256)/rate,4));support.append(float(flux[best]))
    confidence=float(len(beats)/max(1,len(grid))*min(1,np.mean(support)*2)) if support else 0.
    if confidence<.15: beats=[]
    # Energy trajectory, four samples/second, used for shot density and climax.
    clip_count=len(clip)//hop
    local=np.sqrt(np.mean(clip[:clip_count*hop].reshape(-1,hop)**2,axis=1))
    smoothed=uniform_filter1d(local,size=50)
    e=smoothed[::12]; e=e/max(float(e.max()),1e-8)
    times=np.arange(len(e))*.24
    interval=np.flatnonzero((times>=duration*.50)&(times<=duration*.82))
    climax=float(times[interval[np.argmax(e[interval])]]) if len(interval) else duration*.68
    return dict(method='spectral-flux + autocorrelation, không phải AI âm nhạc',start=round(start,4),
                track_duration=meta['duration'],duration=duration,bpm=round(bpm,3),confidence=round(confidence,4),
                beats=sorted(set(beats)),energy=[{'time':round(float(t),3),'value':round(float(v),4)} for t,v in zip(times,e)],
                climax=climax,warnings=[] if beats else ['Nhịp không rõ: planner dùng nhịp độ phong cách, không giả nhận diện beat.'])
