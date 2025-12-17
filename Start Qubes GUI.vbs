Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\bit_f\Projects\Qubes\qubes-gui"
WshShell.Run "cmd /k npm run tauri dev", 1, False
