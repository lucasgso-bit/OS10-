import win32gui
import time

time.sleep(5)

hwnd = win32gui.GetForegroundWindow()

titulo = win32gui.GetWindowText(hwnd)
classe = win32gui.GetClassName(hwnd)

print("Título:", titulo)
print("Classe:", classe)
print("HWND:", hwnd)
