#!/data/data/com.termux/files/usr/bin/env python3
import json, os, shutil, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

MOVIE_DIR = Path.home() / "storage/shared/Movies/MovieApp"
SD_PATH = "/sdcard/Movies/MovieApp"

QUALITIES = {
    "1": ("2160p (4K)", "bv*[height<=?2160]+ba/b[height<=?2160]/b"),
    "2": ("1080p (FHD)", "bv*[height<=?1080]+ba/b[height<=?1080]/b"),
    "3": ("720p (HD)", "bv*[height<=?720]+ba/b[height<=?720]/b"),
    "4": ("480p (SD)", "bv*[height<=?480]+ba/b[height<=?480]/b"),
    "5": ("Best Available", "bv*+ba/b"),
    "6": ("Audio Only (MP3)", "ba/b"),
}

LANGS = {
    "1": ("All Audio Languages (Auto-Mux)", "ALL"),
    "2": ("Original + English", "orig+en"),
    "3": ("Hindi + English", "hi+en"),
    "4": ("Tamil + Telugu + Hindi + English", "ta+te+hi+en"),
    "5": ("Custom ISO Codes (e.g. hi,en,ta,es)", "CUSTOM"),
}

def search_ia(q):
    eq = urllib.parse.quote(f"({q}) AND mediatype:(movies)")
    u = f"https://archive.org/advancedsearch.php?q={eq}&fl[]=identifier&fl[]=title&fl[]=year&fl[]=language&sort[]=downloads+desc&rows=10&page=1&output=json"
    out = []
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "TermuxMovie/2.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            for d in json.loads(r.read().decode()).get("response", {}).get("docs", []):
                i = d.get("identifier")
                if i:
                    out.append({"src": "Archive", "title": f"{d.get('title', i)} ({d.get('year', 'N/A')})", "url": f"https://archive.org/details/{i}"})
    except Exception as e:
        print(f"[!] Archive notice: {e}")
    return out

def search_yt(q):
    out = []
    try:
        p = subprocess.run(["yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings", f"ytsearch10:{q} full movie"], capture_output=True, text=True, timeout=25)
        for line in p.stdout.strip().splitlines():
            if line:
                j = json.loads(line)
                u = j.get("url") or f"https://www.youtube.com/watch?v={j.get('id')}"
                out.append({"src": "Stream", "title": f"{j.get('title','Movie')} [{j.get('duration_string','Stream')}]", "url": u})
    except Exception as e:
        print(f"[!] Stream search notice: {e}")
    return out

def open_player(uri, title, player="vlc"):
    print(f"\n[*] Launching {player.upper()}: {title}")
    act = "is.xyz.mpv/.MPVActivity" if player == "mpv" else "org.videolan.vlc/org.videolan.vlc.gui.video.VideoPlayerActivity"
    r = subprocess.run(["am", "start", "--user", "0", "-a", "android.intent.action.VIEW", "-d", uri, "-n", act, "-e", "title", title], capture_output=True, text=True)
    if r.returncode != 0 or "Error" in (r.stdout + r.stderr):
        subprocess.run(["am", "start", "--user", "0", "-a", "android.intent.action.VIEW", "-t", "video/*", "-d", uri])

def verify_file(fp):
    print("\n" + "=" * 55 + f"\nVERIFYING: {fp.name}\n" + "=" * 55)
    if not fp.exists() or fp.stat().st_size == 0:
        print("[!] FAILED: File empty or missing.")
        return False
    print(f"[+] Size : {fp.stat().st_size / (1024*1024):.2f} MB\n[+] Path : {SD_PATH}/{fp.name}")
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,tags", "-of", "json", str(fp)], capture_output=True, text=True)
    if p.returncode == 0:
        info = json.loads(p.stdout)
        dur = int(float(info.get("format", {}).get("duration", 0) or 0))
        v, a, s = [], [], []
        for st in info.get("streams", []):
            ct, cn = st.get("codec_type"), st.get("codec_name", "?")
            lg = st.get("tags", {}).get("language", "und")
            if ct == "video": v.append(f"{cn} ({st.get('width','?')}x{st.get('height','?')})")
            elif ct == "audio": a.append(f"{cn}[{lg}]")
            elif ct == "subtitle": s.append(f"{cn}[{lg}]")
        print(f"[+] Time : {dur//3600:02d}h:{(dur%3600)//60:02d}m:{dur%60:02d}s")
        print(f"[+] Video: {', '.join(v) or 'None'}\n[+] Audio: {', '.join(a) or 'None'}\n[+] Subs : {', '.join(s) or 'None'}")
        print("[+] Status: PASSED (Verified Playable Container)\n" + "=" * 55)
    return True

def build_fmt(qk, lmode, cust=""):
    _, qe = QUALITIES.get(qk, QUALITIES["2"])
    if qk == "6": return "ba/b", False
    hf = f"[height<=?{qe.split('height<=?')[1].split(']')[0]}]" if "height<=?" in qe else ""
    bv, bf = f"bv*{hf}", f"b{hf}/b"
    if lmode == "ALL": return f"{bv}+mergeall[vcodec=none][format_id!*=drc]/{bv}+ba/{bf}", True
    if lmode == "orig+en": return f"{bv}+(ba[format_note*=original]+ba[language^=en]/ba)/{bf}", True
    codes = [c.strip() for c in (cust.split(",") if lmode == "CUSTOM" else lmode.split("+")) if c.strip()]
    if not codes: return f"{bv}+ba/{bf}", False
    return f"{bv}+({'+'.join(f'ba[language^={c}]' for c in codes)}/{'/'.join(f'ba[language^={c}]' for c in codes)}/ba)/{bf}", True

def preview_movie(url, title):
    MOVIE_DIR.mkdir(parents=True, exist_ok=True)
    mode = input("\nPreview Mode: [1] Instant Live Stream  [2] 30s Sample Clip Verify [default=1]: ").strip() or "1"
    pl = "mpv" if input("Player: [1] VLC  [2] MPV [default=1]: ").strip() == "2" else "vlc"
    if mode == "2":
        smp = MOVIE_DIR / "sample_preview.mkv"
        smp.unlink(missing_ok=True)
        print("[*] Downloading 30s sample clip (00:01:00 to 00:01:30)...")
        subprocess.run(["yt-dlp", "--no-warnings", "--download-sections", "*00:01:00-00:01:30", "-f", "bv*[height<=?720]+ba/b", "--merge-output-format", "mkv", "-o", str(smp), url])
        if smp.exists() and verify_file(smp):
            open_player(f"file://{SD_PATH}/{smp.name}", f"[SAMPLE] {title}", pl)
            return
    p = subprocess.run(["yt-dlp", "-f", "b[height<=?720]/bv*[height<=?720]/b", "-g", "--no-warnings", url], capture_output=True, text=True)
    urls = [u.strip() for u in p.stdout.strip().splitlines() if u.strip()]
    if urls: open_player(urls[0], f"[PREVIEW] {title}", pl)
    else: print("[!] Direct preview unavailable for this source; try Option 2 Download.")

def download_movie(url, title, qk, lmode, cust=""):
    MOVIE_DIR.mkdir(parents=True, exist_ok=True)
    fmt, multi = build_fmt(qk, lmode, cust)
    cmd = ["yt-dlp", "--no-mtime", "--add-metadata", "--ignore-errors", "-o", f"{MOVIE_DIR}/%(title).75s [%(id)s].%(ext)s"]
    if shutil.which("aria2c"): cmd += ["--downloader", "aria2c", "--downloader-args", "aria2c:-x 16 -s 16 -k 1M"]
    if qk == "6": cmd += ["-x", "--audio-format", "mp3", "-f", fmt]
    else:
        cmd += ["-f", fmt, "--merge-output-format", "mkv", "--write-sub", "--write-auto-sub", "--sub-langs", "en.*,hi.*,ta.*,te.*,all,-live_chat", "--embed-subs"]
        if multi: cmd.append("--audio-multistreams")
    cmd.append(url)
    if subprocess.run(cmd).returncode == 0:
        files = [f for f in MOVIE_DIR.glob("*") if f.is_file() and not f.name.endswith(".part")]
        latest = max(files, key=os.path.getctime, default=None)
        if latest and verify_file(latest):
            if (input("\n[?] Open in VLC now to verify playback? (y/n, default=y): ").strip().lower() or "y") == "y":
                open_player(f"file://{SD_PATH}/{latest.name}", latest.name, "vlc")

def local_lib():
    MOVIE_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted([f for f in MOVIE_DIR.glob("*") if f.is_file() and not f.name.startswith(".")], key=os.path.getctime, reverse=True)
    if not files: return print(f"\n[!] No movies in {SD_PATH}")
    for i, f in enumerate(files, 1): print(f"  [{i}] {f.name} ({f.stat().st_size/(1024*1024):.1f} MB)")
    s = input("\nSelect file number to Verify & Play: ").strip()
    if s.isdigit() and 1 <= int(s) <= len(files):
        f = files[int(s)-1]
        verify_file(f)
        open_player(f"file://{SD_PATH}/{f.name}", f.name, "vlc")

def main():
    print("=" * 60 + "\n  TERMUX MOVIE APP: SEARCH, PREVIEW, MULTI-AUDIO & VERIFY\n" + "=" * 60)
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not q:
        c = input("\n[1] Search Movie Online  [2] Verify & Watch Downloaded  [3] Exit\nSelect [default=1]: ").strip() or "1"
        if c == "2": return local_lib()
        if c == "3": return
        q = input("\nEnter Movie Name or URL: ").strip()
    if not q: return
    if q.startswith(("http://", "https://")):
        sel = {"src": "URL", "title": q, "url": q}
    else:
        print(f"\n[*] Searching for '{q}'...")
        res = search_ia(q) + search_yt(q)
        if not res: return print("[!] No results found.")
        for i, r in enumerate(res, 1): print(f"  [{i:2d}] [{r['src']}] {r['title']}")
        idx = input(f"\nSelect Movie (1-{len(res)}): ").strip()
        if not idx.isdigit() or not (1 <= int(idx) <= len(res)): return
        sel = res[int(idx)-1]

    while True:
        print(f"\nSelected: {sel['title']}\n  [1] PREVIEW Movie (Live Stream or 30s Sample Clip)\n  [2] DOWNLOAD Full Movie (Multi-Language + Quality + Verify)\n  [3] INSPECT Audio & Subtitle Tracks (-F)\n  [4] Local Library\n  [5] Exit")
        act = input("Action [1-5]: ").strip()
        if act == "1": preview_movie(sel["url"], sel["title"])
        elif act == "2":
            for k, (d, _) in QUALITIES.items(): print(f"  [{k}] {d}")
            qk = input("Quality [1-6, default=2 (1080p)]: ").strip() or "2"
            for k, (d, _) in LANGS.items(): print(f"  [{k}] {d}")
            lk = input("Language [1-5, default=1 (All)]: ").strip() or "1"
            _, lmode = LANGS.get(lk, LANGS["1"])
            cust = input("ISO codes (e.g. hi,en,ta): ").strip() if lmode == "CUSTOM" else ""
            download_movie(sel["url"], sel["title"], qk, lmode, cust)
        elif act == "3": subprocess.run(["yt-dlp", "--list-subs", "-F", sel["url"]])
        elif act == "4": local_lib()
        elif act == "5": break

if __name__ == "__main__":
    main()
