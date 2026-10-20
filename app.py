#!/data/data/com.termux/files/usr/bin/env python3
import json, os, subprocess, urllib.parse, urllib.request
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
MOVIE_DIR = os.path.expanduser("~/storage/shared/Movies/MovieApp")
os.makedirs(MOVIE_DIR, exist_ok=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MovieHub App</title>
<style>
  :root { --bg: #07090e; --card: #121824; --accent: #e50914; --text: #f8fafc; --muted: #94a3b8; }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, sans-serif; }
  body { background: var(--bg); color: var(--text); padding: 12px; }
  header { text-align: center; padding: 12px 0; border-bottom: 1px solid #1e293b; margin-bottom: 16px; }
  h1 { color: var(--accent); font-size: 1.5rem; }
  .search-box { display: flex; gap: 8px; margin-top: 12px; }
  input, select, button { padding: 10px 12px; border-radius: 8px; border: 1px solid #334155; font-size: 0.95rem; }
  input { flex: 1; background: #0f172a; color: #fff; }
  button { background: var(--accent); color: #fff; border: none; font-weight: 600; cursor: pointer; }
  button.sec { background: #2563eb; }
  .player-card { display: none; background: var(--card); padding: 12px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #1e293b; }
  video { width: 100%; max-height: 380px; background: #000; border-radius: 8px; margin-top: 8px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
  .card { background: var(--card); border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; border: 1px solid #1e293b; cursor: pointer; }
  .card img { width: 100%; height: 220px; object-fit: cover; background: #000; }
  .card-body { padding: 8px; display: flex; flex-direction: column; gap: 4px; flex: 1; }
  .title { font-size: 0.9rem; font-weight: 600; line-height: 1.2; }
  .meta { font-size: 0.75rem; color: var(--muted); }
  #status { text-align: center; padding: 10px; color: var(--muted); font-size: 0.9rem; }
</style>
</head>
<body>
<header>
  <h1>🎬 MovieHub Pro</h1>
  <div class="search-box">
    <input type="text" id="q" placeholder="Search any movie..." value="Night of the Living Dead">
    <button onclick="searchMovies()">Search</button>
  </div>
</header>

<div id="playerCard" class="player-card">
  <h3 id="pTitle" style="font-size:1.1rem; margin-bottom:6px;">Movie Title</h3>
  <p id="pDetails" class="meta" style="margin-bottom:8px;"></p>
  <video id="vid" controls playsinline></video>
  <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;">
    <select id="qualitySel" onchange="changeQual()" style="flex:1; background:#0f172a; color:#fff;"></select>
    <button class="sec" onclick="preview30s()">⏱️ 30s Preview</button>
    <button onclick="downloadMovie()">⬇️ Download</button>
  </div>
</div>

<div id="status">Type a movie name and hit Search</div>
<div id="grid" class="grid"></div>

<script>
let currentMovie = null;

async function searchMovies() {
  const query = document.getElementById('q').value.trim();
  if(!query) return;
  document.getElementById('status').textContent = "Searching online movies...";
  document.getElementById('grid').innerHTML = "";
  
  const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
  const data = await res.json();
  
  if(!data.length) {
    document.getElementById('status').textContent = "No movies found.";
    return;
  }
  document.getElementById('status').textContent = `Found ${data.length} movies:`;
  const grid = document.getElementById('grid');
  
  data.forEach(m => {
    const card = document.createElement('div');
    card.className = 'card';
    card.onclick = () => selectMovie(m.id, m.title);
    card.innerHTML = `
      <img src="${m.thumb}" loading="lazy">
      <div class="card-body">
        <div class="title">${m.title}</div>
        <div class="meta">📅 ${m.year} | 🌐 ${m.lang}</div>
      </div>`;
    grid.appendChild(card);
  });
}

async function selectMovie(id, title) {
  document.getElementById('playerCard').style.display = 'block';
  document.getElementById('playerCard').scrollIntoView({behavior: 'smooth'});
  document.getElementById('pTitle').textContent = title;
  document.getElementById('pDetails').textContent = "Loading streams & details...";
  
  const res = await fetch(`/api/details?id=${id}`);
  const data = await res.json();
  currentMovie = data;
  
  document.getElementById('pDetails').textContent = `Downloads: ${data.downloads} | Creator/Year: ${data.year}`;
  const sel = document.getElementById('qualitySel');
  sel.innerHTML = "";
  
  data.files.forEach((f, idx) => {
    const opt = document.createElement('option');
    opt.value = f.url;
    opt.textContent = `${f.name} (${f.size} MB - ${f.format})`;
    sel.appendChild(opt);
  });
  changeQual();
}

function changeQual() {
  const url = document.getElementById('qualitySel').value;
  if(url) document.getElementById('vid').src = url;
}

function preview30s() {
  const v = document.getElementById('vid');
  v.currentTime = 60;
  v.play().catch(()=>{});
}

async function downloadMovie() {
  if(!currentMovie) return;
  alert("Download started in background! File will save to /sdcard/Movies/MovieApp");
  await fetch(`/api/download?id=${currentMovie.id}&url=${encodeURIComponent(document.getElementById('qualitySel').value)}`);
}

window.onload = searchMovies;
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    eq = urllib.parse.quote(f"({q}) AND mediatype:(movies)")
    url = f"https://archive.org/advancedsearch.php?q={eq}&fl[]=identifier&fl[]=title&fl[]=year&fl[]=downloads&fl[]=language&sort[]=downloads+desc&rows=20&output=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MovieApp/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            docs = json.loads(resp.read().decode()).get("response", {}).get("docs", [])
            out = []
            for d in docs:
                i = d.get("identifier")
                if i:
                    out.append({
                        "id": i,
                        "title": d.get("title", i),
                        "year": d.get("year", "N/A"),
                        "downloads": d.get("downloads", 0),
                        "lang": str(d.get("language", "Multi")),
                        "thumb": f"https://archive.org/services/img/{i}"
                    })
            return jsonify(out)
    except Exception as e:
        return jsonify([])

@app.route("/api/details")
def api_details():
    ident = request.args.get("id", "")
    meta_url = f"https://archive.org/metadata/{ident}"
    try:
        req = urllib.request.Request(meta_url, headers={"User-Agent": "MovieApp/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            meta = json.loads(resp.read().decode())
            files = []
            for f in meta.get("files", []):
                name = f.get("name", "")
                if name.lower().endswith((".mp4", ".mkv", ".webm")):
                    size_mb = round(int(f.get("size", 0) or 0) / (1024*1024), 1)
                    files.append({
                        "name": name,
                        "size": size_mb,
                        "format": f.get("format", "Video"),
                        "url": f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}"
                    })
            files.sort(key=lambda x: x["size"], reverse=True)
            return jsonify({
                "id": ident,
                "year": meta.get("metadata", {}).get("year", "N/A"),
                "downloads": meta.get("metadata", {}).get("downloads", "N/A"),
                "files": files
            })
    except Exception as e:
        return jsonify({"files": []})

@app.route("/api/download")
def api_download():
    url = request.args.get("url", "")
    if url:
        subprocess.Popen(["yt-dlp", "--no-mtime", "-P", MOVIE_DIR, url])
    return jsonify({"status": "started"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
