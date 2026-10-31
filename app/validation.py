"""Measure actual decoded picture/audio, not just the existence of streams."""
import numpy as np
from .engine import ff


def content_metrics(path,duration):
    deviations=[]
    for fraction in (.25,.5,.75):
        raw=ff('-ss',duration*fraction,'-i',path,'-map','0:v:0','-an','-frames:v',1,
               '-vf','scale=64:64','-pix_fmt','rgb24','-f','rawvideo','pipe:1')
        if len(raw)!=64*64*3:raise ValueError('Không đọc được ảnh mẫu từ bản xuất.')
        deviations.append(float(np.std(np.frombuffer(raw,np.uint8))))
    raw=ff('-i',path,'-vn','-ac',1,'-ar',8000,'-f','f32le','pipe:1')
    audio=np.frombuffer(raw,np.float32)
    rms=float(np.sqrt(np.mean(audio**2))) if len(audio) else 0.
    if max(deviations)<2:raise ValueError('Bản xuất chỉ có ảnh phẳng/đen tại các điểm kiểm tra.')
    if rms<1e-5:raise ValueError('Bản xuất không có âm thanh nghe được theo phép đo RMS.')
    return {'image_sample_std':[round(v,4) for v in deviations],'audio_rms':round(rms,7),'picture_and_sound_checked':True}
