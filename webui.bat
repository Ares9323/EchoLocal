@echo off
rem Web interface: pick a voice from voices\, write or translate the text, generate, listen. Opens http://127.0.0.1:7860
call "%~dp0Chatterbox\venv\Scripts\python.exe" "%~dp0WebUI\app.py" %*
