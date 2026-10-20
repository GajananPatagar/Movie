#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y
pkg install -y python ffmpeg aria2 git gh jq fzf termux-api
python -m pip install -U "yt-dlp[default]"
mkdir -p ~/storage/shared/Movies/MovieApp ~/bin
chmod +x ~/Movie/movie_app.py
ln -sf ~/Movie/movie_app.py ~/bin/movie
echo "[+] Installed! Type 'movie' in Termux."
