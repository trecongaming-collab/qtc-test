"""Fetch public test photos, synthesize short sample videos and music locally.
Only public URLs below are requested. No user footage is read or uploaded.
Photos remain in ignored work/ and are never committed.
"""
import json
from pathlib import Path
import sys
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.engine import ff,ambient

ROOT=Path(__file__).resolve().parents[1]/'work'/'ai-samples'
PHOTOS={
    'dog.jpg':'https://github.com/pytorch/hub/raw/refs/heads/master/images/dog.jpg',
    **{name:f'https://github.com/scikit-image/scikit-image/raw/refs/tags/v0.19.3/skimage/data/{name}' for name in ['astronaut.png','coffee.png','chelsea.png','rocket.jpg']},
}


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for index,(name,url) in enumerate(PHOTOS.items()):
        path=ROOT/name
        if not path.exists():
            print(f'Downloading public fixture: {name}',flush=True)
            with urlopen(url,timeout=60) as response:path.write_bytes(response.read())
        target=ROOT/f'sample-{index}.mp4'
        ff('-loop',1,'-i',path,'-vf',"scale=640:640:force_original_aspect_ratio=increase,crop=640:640,zoompan=z='1+on*0.0007':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=1:s=480x480:fps=30",'-t',4.2,'-c:v','libx264','-threads',2,'-pix_fmt','yuv420p',target)
        manifest.append({'video':target.name,'public_photo':name,'source':url})
    ff('-f','lavfi','-i',r'aevalsrc=(0.10+0.30*exp(-pow((t-10.2)/1.5\,2)))*sin(2*PI*180*t)*exp(-mod(t\,0.6)*25):s=44100:d=15',ROOT/'music.wav')
    (ROOT/'fixtures.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Prepared 5 synthetic camera-movement clips from public photos; these are not real travel footage.')

if __name__=='__main__':main()
