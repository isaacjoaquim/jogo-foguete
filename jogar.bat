@echo off
title Rumo ao Espaco - Jogo do Foguete
py main.py
if %ERRORLEVEL% NEQ 0 (
    python main.py
)
pause
