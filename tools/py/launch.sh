cd "$(dirname "$0")/.."
powershell -NoProfile -Command "Start-Process -FilePath 'tools\azahar\azahar-windows-msvc-2127.0.1\azahar.exe' -ArgumentList '\"$1\"' -WindowStyle Minimized"
sleep 10
python -c "import ctypes,sys;sys.path.insert(0,'scripts');import emu;ctypes.windll.user32.ShowWindow(emu.find_main(),4)"
