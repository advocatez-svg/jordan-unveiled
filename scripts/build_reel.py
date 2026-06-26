#!/usr/bin/env python3
"""
Build an actual 9:16 1080x1920 photo-to-video reel for Jordan Unveiled
from the still images already in this repo.

Efficient streaming renderer:
- each photo's blurred-fill base + unified warm grade computed ONCE
- Ken Burns slow zoom is a cheap per-frame crop
- crossfade transitions between segments
- hook title card + CTA end card
- soft generated ambient pad (royalty-free) muxed in

Output: reels-10-builds-v1/renders/jordan_in_20s_v1.mp4
"""
import os, sys, wave, subprocess
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import imageio.v2 as imageio
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "reels-10-builds-v1", "renders")
os.makedirs(OUTDIR, exist_ok=True)
OUT = os.path.join(OUTDIR, "jordan_in_20s_v1.mp4")
FFEXE = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1080, 1920, 30
FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FI = "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf"
def font(sz, it=False): return ImageFont.truetype(FI if it else FB, sz)

def log(m): print(m, flush=True)

S = "samples-3-ig-3-fb-v1"
P = "personal-social-posts-50-v1/IG-4x5-v1"
SEQ = [
    f"{S}/sample_02_instagram_v1.jpg",   # Petra valley wide (hero opener)
    f"{S}/sample_01_instagram_v1.jpg",   # Amman white hills
    f"{P}/post_025_ig_4x5_v1.jpg",       # Roman ruins / columns
    f"{P}/post_020_ig_4x5_v1.jpg",       # Amman misty cityscape
    f"{P}/post_048_ig_4x5_v1.jpg",       # Petra rust landscape
    f"{S}/sample_03_instagram_v1.jpg",   # Petra royal tombs (dramatic close)
]
SECS_PER_PHOTO = 3.2
FADE = 0.5
CARD = 2.2
N_PHOTO = int(SECS_PER_PHOTO*FPS)
N_FADE  = int(FADE*FPS)
N_CARD  = int(CARD*FPS)
ZOOM = 1.10  # ken burns base is pre-scaled by this; we crop a moving window

def grade_np(a):
    a = a.astype(np.float32)*1.04
    a[...,0] = a[...,0]*1.05 + 4
    a[...,2] = a[...,2]*0.97
    a = 255*np.clip(((a/255-0.5)*1.06+0.5),0,1)
    return a

# precompute vignette mask once
_yy,_xx = np.mgrid[0:H,0:W]
_d = np.sqrt(((_xx-W/2)/(W*0.75))**2 + ((_yy-H/2)/(H*0.75))**2)
VIGN = np.clip(1.0-0.28*np.clip(_d-0.5,0,1),0,1)[...,None]

def base_fill(path, darken=1.0):
    """1080x1920 base: darkened blurred cover bg + photo fit to width, centered."""
    im = Image.open(path).convert("RGB")
    bg = im.copy()
    sc = max(W/bg.width, H/bg.height)*1.15
    bg = bg.resize((int(bg.width*sc),int(bg.height*sc)), Image.LANCZOS)
    x=(bg.width-W)//2; y=(bg.height-H)//2
    bg = bg.crop((x,y,x+W,y+H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.eval(bg, lambda p:int(p*0.78))
    fg = im.resize((W,int(im.height*W/im.width)), Image.LANCZOS)
    base = bg.copy(); base.paste(fg,(0,(H-fg.height)//2))
    if darken!=1.0: base = Image.eval(base, lambda p:int(p*darken))
    return base

def photo_kb_base(path):
    """Pre-graded, pre-vignetted, pre-zoomed base ready for cheap window crops."""
    base = base_fill(path)
    big = base.resize((int(W*ZOOM),int(H*ZOOM)), Image.LANCZOS)
    arr = np.asarray(big).astype(np.float32)
    arr = grade_np(arr)
    big = Image.fromarray(arr.astype(np.uint8))
    return big  # size (W*ZOOM, H*ZOOM)

def kb_frame(big, t):
    """t 0..1: pan/zoom window. Start fully zoomed-in (centered) -> ease out to wider."""
    bw,bh = big.size
    # zoom factor 1.08 -> 1.0 (slow push-out feels premium for stills); keep centered
    z = 1.08 - 0.08*t
    cw,ch = int(W*z), int(H*z)
    x=(bw-cw)//2; y=(bh-ch)//2
    fr = big.crop((x,y,x+cw,y+ch)).resize((W,H), Image.LANCZOS)
    a = np.asarray(fr).astype(np.float32)*VIGN
    return Image.fromarray(a.astype(np.uint8))

def draw_center(img, lines):
    d=ImageDraw.Draw(img)
    total=sum(sz+18 for _,sz,_ in lines)
    y=H//2-total//2
    for text,sz,it in lines:
        f=font(sz,it)
        w=d.textbbox((0,0),text,font=f)[2]; x=(W-w)//2
        d.text((x+3,y+3),text,font=f,fill=(0,0,0))
        d.text((x,y),text,font=f,fill=(255,255,255))
        y+=sz+18
    return img

def card(lines, bg_path):
    return draw_center(base_fill(bg_path, darken=0.42), lines)

# ---- writer ----
writer = imageio.get_writer(OUT, fps=FPS, codec="libx264",
                            macro_block_size=8,
                            ffmpeg_params=["-crf","21","-preset","medium","-pix_fmt","yuv420p"])
def emit(img): writer.append_data(np.asarray(img))
emitted=0
def emit_count(img):
    global emitted; emit(img); emitted+=1

log("rendering cards + bases...")
hook = card([("JORDAN",150,False),("in 20 seconds",62,True)], SEQ[0])
cta  = card([("Save this trip",110,False),("Follow for more Jordan",54,True),
             ("@jordan.unveiled.co",50,False)], SEQ[-1])

# Build generators of frames per segment (streamed, low memory)
def seg_frames(kind, payload):
    if kind=="card":
        for _ in range(N_CARD): yield payload
    else:  # photo
        big = photo_kb_base(payload)
        for i in range(N_PHOTO):
            yield kb_frame(big, i/(N_PHOTO-1))

SEGMENTS = [("card",hook)] + [("photo",p) for p in SEQ] + [("card",cta)]

# To crossfade we need the last N_FADE frames of prev and first N_FADE of next.
prev_tail=[]
for si,(kind,payload) in enumerate(SEGMENTS):
    log(f"segment {si+1}/{len(SEGMENTS)} ({kind})")
    frames = list(seg_frames(kind,payload))   # one segment at a time = small
    if si==0:
        for fr in frames[:-N_FADE]: emit_count(fr)
        prev_tail = frames[-N_FADE:]
    else:
        head = frames[:N_FADE]
        for k in range(N_FADE):
            a=prev_tail[k]; b=head[k] if k<len(head) else frames[-1]
            emit_count(Image.blend(a,b,(k+1)/(N_FADE+1)))
        if si<len(SEGMENTS)-1:
            for fr in frames[N_FADE:-N_FADE]: emit_count(fr)
            prev_tail=frames[-N_FADE:]
        else:
            for fr in frames[N_FADE:]: emit_count(fr)

writer.close()
dur = emitted/FPS
log(f"VIDEO done: {emitted} frames, {dur:.1f}s")

# ---- royalty-free ambient pad ----
sr=44100; n=int(sr*dur); t=np.arange(n)/sr
def voice(f,a):
    vib=1+0.003*np.sin(2*np.pi*0.2*t); return a*np.sin(2*np.pi*f*vib*t)
audio=voice(110,0.18)+voice(164.81,0.13)+voice(220,0.10)+voice(329.63,0.05)
env=(0.5+0.5*np.sin(np.pi*(t/dur)))*np.clip(t/1.5,0,1)*np.clip((dur-t)/1.5,0,1)
audio=np.clip(audio*env*0.5,-1,1)
wavp=os.path.join(OUTDIR,"_pad.wav")
with wave.open(wavp,'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((audio*32767).astype('<i2').tobytes())
tmp=os.path.join(OUTDIR,"_mux.mp4")
subprocess.run([FFEXE,"-y","-i",OUT,"-i",wavp,"-c:v","copy","-c:a","aac",
                "-b:a","160k","-shortest",tmp],check=True,capture_output=True)
os.replace(tmp,OUT); os.remove(wavp)
log(f"FINAL: {OUT}  {dur:.1f}s")
