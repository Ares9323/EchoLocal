@echo off
rem Every texts\<lang>.txt -> outputs\<lang>\001.wav, ... with the same voice, then a Whisper check.
rem Extra arguments go to speak.py, e.g.  speak_all.bat --ref voices\my_voice.m4a --exaggeration 0.7
call "%~dp0Chatterbox\speak.bat" %*
if errorlevel 1 exit /b %errorlevel%
call "%~dp0Whisper\check.bat"
