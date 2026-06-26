#!/usr/bin/env python3
"""Build 3 distinct sample reels from the user's own Jordan clips."""
import subprocess, os, imageio_ffmpeg, numpy as np, wave
from PIL import Image, ImageDraw, ImageFont
FF = imageio_ffmpeg.get_ffmpeg_exe()
SRC = "extracted/for insta"
WORK = "segs"; os.makedirs(WORK, exist_ok=True)
FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FI = "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf"
RENDERS = "/home/user/jordan-unveiled/reels-10-builds-v1/renders"
W,H = 1080,1920
COVER = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"

def font(sz,it=False): return ImageFont.truetype(FI if it else FB, sz)
def make_png(path, lines):
    img=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    for text,sz,it,y in lines:
        f=font(sz,it); w=d.textbbox((0,0),text,font=f)[2]; x=(W-w)//2
        d.text((x+3,y+3),text,font=f,fill=(0,0,0,150))
        d.text((x,y),text,font=f,fill=(255,255,255,255))
    img.save(path)

def build(tag, grade, fade, segs):
    norm=[]
    for i,(fn,ss,dur,lines,tf) in enumerate(segs):
        src=os.path.join(SRC,fn); o=os.path.join(WORK,f"{tag}_{i}.mp4")
        if lines:
            png=os.path.join(WORK,f"{tag}_{i}.png"); make_png(png,lines)
            cmd=[FF,"-y","-ss",str(ss),"-i",src,"-loop","1","-i",png,"-t",str(dur),
                 "-filter_complex",
                 f"[0:v]{COVER},{grade}[bg];[1:v]fade=t=in:st={tf}:d=0.4:alpha=1[tx];"
                 f"[bg][tx]overlay=0:0,format=yuv420p[v]",
                 "-map","[v]","-r","30","-an","-c:v","libx264","-crf","19","-preset","medium",o]
        else:
            cmd=[FF,"-y","-ss",str(ss),"-i",src,"-t",str(dur),
                 "-vf",f"{COVER},{grade},format=yuv420p","-r","30","-an",
                 "-c:v","libx264","-crf","19","-preset","medium",o]
        r=subprocess.run(cmd,capture_output=True,text=True)
        if r.returncode!=0: print("ERR",tag,i,fn); print(r.stderr[-1200:]); raise SystemExit(1)
        norm.append((o,dur))
    # xfade
    inputs=[];
    for o,_ in norm: inputs+=["-i",o]
    durs=[d for _,d in norm]; fc=[]; label="0:v"; off=durs[0]-fade
    for i in range(1,len(norm)):
        out=f"x{i}"; fc.append(f"[{label}][{i}:v]xfade=transition=fade:duration={fade}:offset={off:.3f}[{out}]")
        label=out
        if i<len(norm)-1: off+=durs[i]-fade
    total=sum(durs)-fade*(len(norm)-1)
    silent=os.path.join(WORK,f"{tag}_v.mp4")
    cmd=[FF,"-y"]+inputs+["-filter_complex",";".join(fc),"-map",f"[{label}]",
         "-c:v","libx264","-crf","20","-preset","medium","-pix_fmt","yuv420p",silent]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode!=0: print(r.stderr[-1500:]); raise SystemExit(1)
    # pad
    sr=44100; n=int(sr*total); t=np.arange(n)/sr
    def voice(f,a): vib=1+0.003*np.sin(2*np.pi*0.2*t); return a*np.sin(2*np.pi*f*vib*t)
    audio=voice(110,0.18)+voice(164.81,0.13)+voice(220,0.10)+voice(329.63,0.05)
    env=(0.5+0.5*np.sin(np.pi*(t/total)))*np.clip(t/1.2,0,1)*np.clip((total-t)/1.2,0,1)
    audio=np.clip(audio*env*0.5,-1,1)
    wav=os.path.join(WORK,f"{tag}.wav")
    with wave.open(wav,'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((audio*32767).astype('<i2').tobytes())
    out=os.path.join(RENDERS,f"sample_{tag}.mp4")
    cmd=[FF,"-y","-i",silent,"-i",wav,"-c:v","copy","-c:a","aac","-b:a","160k","-shortest",out]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode!=0: print(r.stderr[-1200:]); raise SystemExit(1)
    print(f"sample_{tag}.mp4  ~{total:.1f}s")

# ---- A: Golden Hour (calm, warm) ----
gradeA="eq=contrast=1.05:brightness=0.015:saturation=1.16:gamma=1.03,colorbalance=rm=0.06:gm=0.01:bm=-0.06,vignette=PI/5"
build("A_golden_hour", gradeA, 0.6, [
    ("20250809_062317.mp4",44.0,3.8,[("JORDAN",120,False,720),("golden hour",58,True,860)],0.2),
    ("20250808_210830.mp4",9.0,3.4,[("Where the sun melts",62,False,150)],0.3),
    ("20250612_193537.mp4",15.0,3.4,[("Amman at dusk",66,False,150)],0.3),
    ("20250809_061744.mp4",22.0,3.8,[("Save this for Jordan",68,False,720),("@jordan.unveiled.co",44,True,825)],0.3),
])

# ---- B: Road Trip (energetic, fast) ----
gradeB="eq=contrast=1.10:brightness=0.01:saturation=1.18:gamma=1.0,colorbalance=rm=0.03:gm=0.0:bm=-0.03,vignette=PI/5"
build("B_road_trip", gradeB, 0.4, [
    ("20250809_201148-CINEMATIC.mp4",1.2,2.8,[("ROAD TRIP",104,False,760),("through Jordan",54,True,880)],0.2),
    ("20250612_192337.mp4",12.0,2.4,[],0.0),
    ("20260116_150341.mp4",3.0,2.4,[("Open roads",60,False,150)],0.2),
    ("20260116_151800.mp4",4.0,2.4,[],0.0),
    ("20250612_192542.mp4",45.0,2.8,[("Save this drive",66,False,740),("@jordan.unveiled.co",44,True,845)],0.2),
])

# ---- C: Petra (cinematic) ----
gradeC="eq=contrast=1.09:brightness=0.012:saturation=1.12:gamma=1.0,colorbalance=rm=0.05:gm=0.01:bm=-0.04,vignette=PI/5"
build("C_petra", gradeC, 0.5, [
    ("VID_23751024_003039_148.mp4",0.8,3.6,[("WELCOME TO PETRA",80,False,760)],0.2),
    ("VID_23660317_113807_711.mp4",5.5,3.0,[("A wonder of the world",58,False,820)],0.3),
    ("VID_23750106_233523_820.mp4",3.5,3.4,[("2,000 years old",74,False,820)],0.3),
    ("VID_23770729_143310_647.mp4",0.1,3.0,[("Save Petra",78,False,720),("@jordan.unveiled.co",44,True,825)],0.3),
])
print("ALL DONE")
