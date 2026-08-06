@echo off
setlocal
rem ============================================================
rem  ATLAS - Instalacao automatica (rode UMA vez, dois cliques)
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  ==========================================================
echo    ATLAS - Instalacao automatica
echo  ==========================================================
echo.

rem ---------- 1. Localizar o Python ----------
set "PYCMD="
python --version >nul 2>&1 && set "PYCMD=python"
if not defined PYCMD (
    py --version >nul 2>&1 && set "PYCMD=py"
)
if not defined PYCMD (
    echo  [ERRO] Python nao encontrado neste computador.
    echo.
    echo  Faca assim:
    echo   1. Baixe em https://www.python.org/downloads/
    echo   2. Na instalacao, MARQUE a caixa "Add python.exe to PATH"
    echo   3. Rode este arquivo de novo.
    echo.
    pause
    exit /b 1
)
echo  [OK] Python encontrado:
%PYCMD% --version
echo.

rem ---------- 2. Criar o ambiente virtual ----------
if exist .venv\Scripts\python.exe (
    echo  [OK] Ambiente virtual ja existe (.venv) - pulando criacao.
) else (
    echo  Criando ambiente virtual (.venv)...
    %PYCMD% -m venv .venv
    if errorlevel 1 (
        echo  [ERRO] Nao consegui criar o ambiente virtual.
        pause
        exit /b 1
    )
    echo  [OK] Ambiente virtual criado.
)
echo.

rem ---------- 3. Instalar dependencias ----------
echo  Instalando dependencias (pode levar 1-2 minutos)...
echo.
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  [ERRO] Falha ao instalar dependencias.
    echo  Confira sua conexao com a internet e rode de novo.
    pause
    exit /b 1
)
echo.
echo  [OK] Dependencias instaladas.
echo.

rem ---------- 4. Criar o .env ----------
if exist .env (
    echo  [OK] Arquivo .env ja existe - mantido como esta.
) else (
    copy /y .env.example .env >nul
    echo  [OK] Arquivo .env criado (a partir do .env.example).
)
echo.

echo  ==========================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO!
echo  ==========================================================
echo.
echo  Proximos passos (uma so vez):
echo.
echo  1. ESCOLHA A IA:
echo     a) GRATIS E LOCAL - instale o Ollama em https://ollama.com
echo        e rode no terminal:  ollama pull llama3.1
echo     b) API PAGA - abra o arquivo .env em qualquer editor e
echo        cole sua chave (instrucoes dentro do proprio arquivo).
echo.
echo  2. PUBLICAR NO WORDPRESS (opcional): preencha WP_USER e
echo     WP_APP_PASSWORD no .env com a "Senha de Aplicacao" do WP
echo     (Painel do WP -^> Usuarios -^> Perfil -^> Senhas de Aplicacao).
echo.
echo  3. Para usar o agente: dois cliques em "Abrir Painel Atlas.bat".
echo.

set /p ABRIR="Quer abrir o painel agora? (s/n): "
if /i "%ABRIR%"=="s" (
    if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
    echo.
    echo  Abrindo http://127.0.0.1:5000 ...
    echo  (esta janela precisa ficar aberta enquanto voce usa o painel)
    start "" http://127.0.0.1:5000
    .venv\Scripts\python.exe painel.py --no-browser
)

echo.
echo  Instalador encerrado. Ate mais!
pause
endlocal
