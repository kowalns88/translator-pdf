@echo off
REM =============================================================================
REM PDF Translator - Skrypt uruchomieniowy (Windows)
REM =============================================================================
REM Uzycie:
REM   run.bat plik.pdf              - tlumaczy caly plik
REM   run.bat plik.pdf 1-10         - tlumaczy strony 1-10
REM   run.bat plik.pdf 1-50 wynik.pdf  - tlumaczy strony 1-50, zapisuje jako wynik.pdf
REM =============================================================================

setlocal enabledelayedexpansion

set INPUT_FILE=%~1
set PAGES=%~2
set OUTPUT_FILE=%~3

if "%INPUT_FILE%"=="" (
    echo ================================================================
    echo          PDF Translator - English to Polish
    echo ================================================================
    echo.
    echo  Uzycie:
    echo    run.bat plik.pdf              ^(caly plik^)
    echo    run.bat plik.pdf 1-10         ^(strony 1-10^)
    echo    run.bat plik.pdf 1-50 wynik.pdf
    echo.
    echo ================================================================
    exit /b 1
)

REM Sprawdz czy plik istnieje
if not exist "%INPUT_FILE%" (
    echo [BLAD] Plik nie znaleziony: %INPUT_FILE%
    exit /b 1
)

REM Sprawdz czy Docker jest zainstalowany
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo [BLAD] Docker nie jest zainstalowany!
    echo.
    echo Zainstaluj Docker Desktop:
    echo   https://www.docker.com/products/docker-desktop/
    echo.
    exit /b 1
)

REM Zbuduj obraz
echo [INFO] Przygotowywanie srodowiska...
docker build -t pdf-translator . -q

REM Przygotuj argumenty
set DOCKER_ARGS=--input /data/%~nx1

if not "%PAGES%"=="" (
    set DOCKER_ARGS=!DOCKER_ARGS! --pages %PAGES%
)

if not "%OUTPUT_FILE%"=="" (
    set DOCKER_ARGS=!DOCKER_ARGS! --output /data/%OUTPUT_FILE%
)

REM Uruchom tlumaczenie
echo [INFO] Rozpoczynam tlumaczenie...
echo.

docker run --rm -v "%~dp1":/data pdf-translator %DOCKER_ARGS%

echo.
echo [OK] Gotowe!
