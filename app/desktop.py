"""Windows local-file GUI: no browser upload, no input copies, no external API."""
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import uuid


def main():
    import tkinter as tk
    from tkinter import filedialog,messagebox,ttk
    from .profiles import PROFILES
    from .vision import readiness
    root=tk.Tk();root.title('QTC AI VIDEO EDITOR · Video lớn trên máy');root.geometry('620x710')
    root.minsize(560,680)
    frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
    videos=[];music=None;output=Path(__file__).resolve().parent.parent/'output'
    events=queue.SimpleQueue();current_result=None
    ttk.Label(frame,text='QTC AI VIDEO EDITOR',font=('Segoe UI',18,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Đọc trực tiếp video trên ổ đĩa. Không tải lên hoặc sao chép nguồn.').pack(anchor='w',pady=(6,18))
    sources=tk.StringVar(value='Chưa chọn video');track=tk.StringVar(value='Chưa chọn nhạc');location=tk.StringVar(value=str(output))
    status=tk.StringVar(value=readiness()['message'])
    def choose_videos():
        nonlocal videos
        chosen=filedialog.askopenfilenames(title='Chọn 5–20 video DJI',filetypes=[('Video','*.mp4 *.MP4 *.mov *.MOV *.mkv *.m4v')])
        if chosen:videos=[Path(p) for p in chosen];sources.set(f'Đã chọn {len(videos)} video')
    def choose_music():
        nonlocal music
        chosen=filedialog.askopenfilename(title='Chọn nhạc',filetypes=[('Audio','*.mp3 *.wav *.m4a *.aac *.flac *.ogg')])
        if chosen:music=Path(chosen);track.set(music.name)
    def choose_output():
        nonlocal output
        chosen=filedialog.askdirectory(title='Chọn thư mục lưu bản dựng')
        if chosen:output=Path(chosen);location.set(str(output))
    for text,command,variable in [('1. Chọn video',choose_videos,sources),('2. Chọn nhạc',choose_music,track),('3. Nơi lưu MP4',choose_output,location)]:
        row=ttk.Frame(frame);row.pack(fill='x',pady=5)
        ttk.Button(row,text=text,command=command).pack(side='left')
        ttk.Label(row,textvariable=variable,wraplength=370).pack(side='left',padx=12)
    choices=ttk.Frame(frame);choices.pack(fill='x',pady=18)
    style=tk.StringVar(value='Cinematic Travel');resolution=tk.StringVar(value='1080p');aspect=tk.StringVar(value='9:16');duration=tk.IntVar(value=36)
    rows=[('Phong cách',style,[p['name'] for p in PROFILES.values()]),('Độ phân giải',resolution,['1080p','4k']),('Tỷ lệ',aspect,['9:16','16:9'])]
    for i,(label,variable,values) in enumerate(rows):
        ttk.Label(choices,text=label).grid(row=i,column=0,sticky='w',pady=4)
        ttk.Combobox(choices,textvariable=variable,values=values,state='readonly',width=28).grid(row=i,column=1,padx=20,pady=4)
    ttk.Label(choices,text='Thời lượng (giây)').grid(row=3,column=0,sticky='w',pady=4)
    ttk.Spinbox(choices,from_=15,to=90,textvariable=duration,width=28).grid(row=3,column=1,padx=20,pady=4)
    progress=ttk.Progressbar(frame,maximum=100);progress.pack(fill='x',pady=10)
    ttk.Label(frame,textvariable=status,wraplength=550).pack(anchor='w',pady=5)
    def run_edit(paths,song,folder,options):
        try:
            from .ai_editor import render_ai
            render_ai(paths,song,folder,update=lambda p,m:events.put(('progress',p,m)),**options)
            events.put(('done',folder/'result.mp4'))
        except Exception as error:events.put(('error',str(error)))
    def start():
        nonlocal current_result
        if not readiness()['ready']:messagebox.showerror('Chưa cài AI','Chạy setup-ai-windows.cmd trước.');return
        if not 5<=len(videos)<=20 or music is None:messagebox.showerror('Thiếu nguồn','Chọn 5–20 video và một bản nhạc.');return
        try:seconds=duration.get()
        except tk.TclError:seconds=0
        if not 15<=seconds<=90:messagebox.showerror('Thời lượng','Chọn 15–90 giây.');return
        key=next(k for k,v in PROFILES.items() if v['name']==style.get())
        folder=output/('QTC-'+uuid.uuid4().hex[:12]);current_result=None
        build.config(state='disabled');open_button.config(state='disabled');progress['value']=0
        options=dict(duration=seconds,style=key,resolution=resolution.get(),aspect=aspect.get())
        threading.Thread(target=run_edit,args=(list(videos),music,folder,options),daemon=True).start()
    def open_result():
        if current_result is None:return
        if os.name=='nt':os.startfile(str(current_result))
        else:subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(current_result)])
    build=ttk.Button(frame,text='AI dựng video',command=start);build.pack(fill='x',pady=8)
    open_button=ttk.Button(frame,text='Mở video đã xuất',command=open_result,state='disabled');open_button.pack(fill='x')
    ttk.Label(frame,text='CPU · không phí API · 4K có thể mất nhiều thời gian',foreground='#666').pack(anchor='w',pady=10)
    def poll():
        nonlocal current_result
        while not events.empty():
            event=events.get()
            if event[0]=='progress':progress['value']=event[1];status.set(event[2])
            elif event[0]=='done':
                current_result=event[1];progress['value']=100;status.set(f'Đã lưu: {current_result}')
                build.config(state='normal');open_button.config(state='normal')
            else:status.set('Dựng không thành công');build.config(state='normal');messagebox.showerror('Không dựng được video',event[1])
        root.after(150,poll)
    def close():
        if str(build['state'])=='disabled':
            messagebox.showinfo('Đang dựng','Hãy chờ bản dựng hoàn tất trước khi đóng cửa sổ.');return
        root.destroy()
    root.protocol('WM_DELETE_WINDOW',close)
    root.after(150,poll);root.mainloop()

if __name__=='__main__':main()
