"""Explicit style controls; no random scene cuts."""
PROFILES={
 'cinematic':dict(name='Cinematic Travel',shot_seconds=3.5,saturation=1.07,contrast=1.025,transition=.22,ramp=True,nature=.26),
 'luxury':dict(name='Luxury',shot_seconds=3.7,saturation=.96,contrast=1.035,transition=.32,ramp=False,nature=.15),
 'energetic':dict(name='Energetic',shot_seconds=2.3,saturation=1.12,contrast=1.04,transition=.10,ramp=True,nature=.22),
 'relaxing':dict(name='Relaxing',shot_seconds=3.7,saturation=1.02,contrast=1.01,transition=.40,ramp=False,nature=.38),
 'tiktok':dict(name='TikTok Viral',shot_seconds=1.65,saturation=1.14,contrast=1.05,transition=.08,ramp=True,nature=.12),
}


def dimensions(resolution,aspect):
    if resolution not in ('1080p','4k') or aspect not in ('9:16','16:9'):
        raise ValueError('Chọn Full HD/4K và tỷ lệ 9:16/16:9 hợp lệ.')
    short,long=(1080,1920) if resolution=='1080p' else (2160,3840)
    return (short,long) if aspect=='9:16' else (long,short)
