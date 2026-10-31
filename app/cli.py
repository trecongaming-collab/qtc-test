"""Direct local-file editing: avoids uploading/copying large DJI footage."""
import argparse
from pathlib import Path
from .ai_editor import render_ai
from .profiles import PROFILES


def main():
    parser=argparse.ArgumentParser(description='QTC local AI video editor')
    parser.add_argument('--videos',nargs='+',required=True,type=Path)
    parser.add_argument('--music',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--duration',type=int,default=36)
    parser.add_argument('--style',choices=PROFILES,default='cinematic')
    parser.add_argument('--resolution',choices=['1080p','4k'],default='1080p')
    parser.add_argument('--aspect',choices=['9:16','16:9'],default='9:16')
    parser.add_argument('--variant',type=int,default=0)
    args=parser.parse_args()
    if not 5<=len(args.videos)<=20:parser.error('Chọn 5–20 video')
    if not 15<=args.duration<=90:parser.error('Thời lượng 15–90 giây')
    if any(not p.is_file() for p in [*args.videos,args.music]):parser.error('Không tìm thấy tệp nguồn/nhạc')
    if args.output.exists() and any(args.output.iterdir()):parser.error('Chọn thư mục output mới/rỗng để tránh ghi đè bản dựng')
    report=render_ai(
        args.videos,args.music,args.output,args.duration,args.style,args.resolution,args.aspect,args.variant,
        update=lambda p,m:print(f'{p}% {m}',flush=True))
    print(f'Finished: {args.output/"result.mp4"} ({report["output"]["duration"]:.2f}s)')

if __name__=='__main__':main()
