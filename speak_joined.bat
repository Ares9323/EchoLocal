@echo off
rem Like speak_all.bat, but one outputs\<lang>.wav per language: lines joined with a short pause.
rem Extra arguments go to speak.py, e.g.  speak_joined.bat --pause 0.8 --ref voices\my_voice.m4a
call "%~dp0Chatterbox\speak.bat" --join %*
if errorlevel 1 exit /b %errorlevel%
call "%~dp0Whisper\check.bat"
