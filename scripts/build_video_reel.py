#!/usr/bin/env python3
"""Build a real edited 9:16 reel from the user's own Jordan video clips.
Text is rendered as transparent PNG overlays (bundled ffmpeg lacks drawtext)."""
import subprocess, os, imageio_ffmpeg, numpy as np, wave
from PIL import Image, ImageDraw, ImageFont
FF = imageio_ffmpeg.get_ffmpeg_exe()
SRC = "extracted/for insta"
WORK = "segs"; os.makedirs(WORK, exist_ok=True)
FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FI = "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf"
OUT = "/home/user/jordan-unveiled/reels-10-builds-v1/renders/jordan_reel_v1.mp4"
W,H = 1080,1920
GRADE = ("eq=contrast=1.07:brightness=0.012:saturation=1.14:gamma=1.02,"
         "colorbalance=rm=0.04:gm=0.01:bm=-0.04,vignette=PI/5")
COVER = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
FADE = 0.5

def font(sz,it=False): return ImageFont.truetype(FI if it else FB, sz)

def make_text_png(path, lines):
    """lines = [(text,size,italic,y)] centered horizontally, white + shadow, transparent bg."""
    img = Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    for text,sz,it,y in lines:
        f=font(sz,it); w=d.textbbox((0,0),text,font=f)[2]; x=(W-w)//2
        d.text((x+3,y+3),text,font=f,fill=(0,0,0,150))
        d.text((x,y),text,font=f,fill=(255,255,255,255))
    img.save(path)

# (filename, start, dur, text_png_lines, text_fade_start)
SEGS = [
    ("VID_23751024_003039_148.mp4", 0.8, 3.6,
        [("THIS IS JORDAN",96,False,740),("Petra · the Siq",50,True,860)], 0.2),
    ("VID_23750106_233523_820.mp4", 3.5, 3.6,
        [("2,000 years old",78,False,810)], 0.3),
    ("VID_23770729_143310_647.mp4", 0.1, 3.0, [], 0.0),
    ("20250809_062317.mp4", 44.0, 3.6,
        [("Golden hour",80,False,810)], 0.3),
    ("20250809_061744.mp4", 22.0, 3.6,
        [("Save this for Jordan",70,False,720),("@jordan.unveiled.co",46,True,830)], 0.3),
]

norm=[]
for i,(fn,ss,dur,lines,tf) in enumerate(SEGS):
    src=os.path.join(SRC,fn); o=os.path.join(WORK,f"n{i}.mp4")
    if lines:
        png=os.path.join(WORK,f"t{i}.png"); make_text_png(png,lines)
        cmd=[FF,"-y","-ss",str(ss),"-i",src,"-loop","1","-i",png,"-t",str(dur),
             "-filter_complex",
             f"[0:v]{COVER},{GRADE}[bg];"
             f"[1:v]fade=t=in:st={tf}:d=0.4:alpha=1[tx];"
             f"[bg][tx]overlay=0:0:format=auto,format=yuv420p[v]",
             "-map","[v]","-r","30","-an","-c:v","libx264","-crf","19","-preset","medium",o]
    else:
        cmd=[FF,"-y","-ss",str(ss),"-i",src,"-t",str(dur),
             "-vf",f"{COVER},{GRADE},format=yuv420p","-r","30","-an",
             "-c:v","libx264","-crf","19","-preset","medium",o]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode!=0: print("ERR",i,fn); print(r.stderr[-1500:]); raise SystemExit(1)
    norm.append((o,dur)); print(f"seg {i} ok: {fn}")

# xfade chain
inputs=[];
for o,_ in norm: inputs+=["-i",o]
durs=[d for _,d in norm]; fc=[]; label="0:v"; off=durs[0]-FADE
for i in range(1,len(norm)):
    out=f"v{i}"
    fc.append(f"[{label}][{i}:v]xfade=transition=fade:duration={FADE}:offset={off:.3f}[{out}]")
    label=out
    if i<len(norm)-1: off+=durs[i]-FADE
total=sum(durs)-FADE*(len(norm)-1)
silent=os.path.join(WORK,"v_only.mp4")
cmd=[FF,"-y"]+inputs+["-filter_complex",";".join(fc),"-map",f"[{label}]",
     "-c:v","libx264","-crf","20","-preset","medium","-pix_fmt","yuv420p",silent]
r=subprocess.run(cmd,capture_output=True,text=True)
if r.returncode!=0: print(r.stderr[-2000:]); raise SystemExit(1)
print(f"xfade total ~{total:.1f}s")

# ambient pad + mux
sr=44100; n=int(sr*total); t=np.arange(n)/sr
def voice(f,a):
    vib=1+0.003*np.sin(2*np.pi*0.2*t); return a*np.sin(2*np.pi*f*vib*t)
audio=voice(110,0.18)+voice(164.81,0.13)+voice(220,0.10)+voice(329.63,0.05)
env=(0.5+0.5*np.sin(np.pi*(t/total)))*np.clip(t/1.5,0,1)*np.clip((total-t)/1.5,0,1)
audio=np.clip(audio*env*0.5,-1,1)
wav=os.path.join(WORK,"pad.wav")
with wave.open(wav,'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((audio*32767).astype('<i2').tobytes())
os.makedirs(os.path.dirname(OUT),exist_ok=True)
cmd=[FF,"-y","-i",silent,"-i",wav,"-c:v","copy","-c:a","aac","-b:a","160k","-shortest",OUT]
r=subprocess.run(cmd,capture_output=True,text=True)
if r.returncode!=0: print(r.stderr[-1500:]); raise SystemExit(1)
print("FINAL:",OUT)
