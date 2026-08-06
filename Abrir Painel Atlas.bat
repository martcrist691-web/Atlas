@echo off
rem ============================================================
rem  ATLAS - Abrir o painel no navegador (dois cliques aqui)
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo.
    echo  AVISO: o Atlas ainda nao foi instalado nesta pasta.
    echo  Rode primeiro o arquivo "Instalar Atlas.bat" (dois cliques).
    echo.
    pause
    exit /b 1
)

echo.
echo   Iniciando o painel do Atlas em http://127.0.0.1:5000
echo   O navegador vai abrir sozinho.
echo   NAO FECHE esta janela enquanto estiver usando o painel.
echo   (Para encerrar: feche esta janela ou aperte Ctrl+C)
echo.

python painel.py
if errorlevel 1 py painel.py
if errorlevel 1 (
    echo.
    echo ERRO: Python nao encontrado. Instale pelo https://python.org
    echo marcando a opcao "Add python to PATH".
)

echo.
echo O painel foi encerrado.
pause
