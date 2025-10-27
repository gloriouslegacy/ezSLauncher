@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo ezSLauncher EXE 빌드
echo ========================================
echo.

REM Python 설치 확인
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python을 먼저 설치해주세요: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [확인] Python 설치됨
python --version
echo.

REM PyInstaller 설치 확인 및 설치
echo PyInstaller 확인 중...
pip show pyinstaller >nul 2>&1
if %errorLevel% neq 0 (
    echo PyInstaller가 설치되어 있지 않습니다.
    echo PyInstaller를 설치합니다...
    pip install pyinstaller
    if %errorLevel% neq 0 (
        echo [오류] PyInstaller 설치 실패
        pause
        exit /b 1
    )
)

echo [확인] PyInstaller 설치됨
echo.

REM 기존 빌드 폴더 삭제
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ezSLauncher.spec del /q ezSLauncher.spec
echo 이전 빌드 폴더 정리 완료
echo.

REM 아이콘 파일 확인 및 경로 설정
set ICON_PATH=
set ADD_DATA_OPTION=

if exist "icon\icon.ico" (
    echo [확인] 아이콘 파일 발견: icon\icon.ico
    set ICON_PATH=icon\icon.ico
    set ADD_DATA_OPTION=--add-data "icon\icon_title.ico;icon"
) else if exist "icon.ico" (
    echo [확인] 아이콘 파일 발견: icon.ico
    set ICON_PATH=icon.ico
    set ADD_DATA_OPTION=--add-data "icon_title.ico;."
) else (
    echo [경고] 아이콘 파일이 없습니다. 기본 아이콘으로 빌드됩니다.
    echo 아이콘을 추가하려면 icon.ico 파일을 스크립트와 같은 폴더에 두세요.
)

REM PNG 파일도 확인 (대체 아이콘으로 사용)
if exist "icon\icon.png" (
    echo [확인] PNG 아이콘 파일도 발견: icon\icon.png
    if defined ADD_DATA_OPTION (
        set ADD_DATA_OPTION=%ADD_DATA_OPTION% --add-data "icon\icon.png;icon"
    ) else (
        set ADD_DATA_OPTION=--add-data "icon\icon.png;icon"
    )
) else if exist "icon.png" (
    echo [확인] PNG 아이콘 파일도 발견: icon.png
    if defined ADD_DATA_OPTION (
        set ADD_DATA_OPTION=%ADD_DATA_OPTION% --add-data "icon.png;."
    ) else (
        set ADD_DATA_OPTION=--add-data "icon.png;."
    )
)
echo.

REM EXE 빌드
echo ========================================
echo EXE 파일 빌드 시작...
echo ========================================
echo.

if defined ICON_PATH (
    echo 아이콘 적용: %ICON_PATH%
    pyinstaller --onefile ^
        --windowed ^
        --name "ezSLauncher" ^
        --clean ^
        --uac-admin ^
        --version-file "version_info.txt" ^
        --icon="%ICON_PATH%" ^
        %ADD_DATA_OPTION% ^
        ezSLauncher.py
) else (
    echo 아이콘 없이 빌드
    pyinstaller --onefile ^
        --windowed ^
        --name "ezSLauncher" ^
        --clean ^
        ezSLauncher.py
)

if %errorLevel% neq 0 (
    echo.
    echo [오류] 빌드 실패
    echo.
    echo 문제 해결 방법:
    echo 1. ezSLauncher.py 파일이 같은 폴더에 있는지 확인
    echo 2. Python 경로가 제대로 설정되어 있는지 확인
    echo 3. 안티바이러스가 빌드를 차단하지 않는지 확인
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 빌드 완료!
echo ========================================
echo.

REM 빌드 결과물 확인
if exist "dist\ezSLauncher.exe" (
    echo [성공] EXE 파일이 생성되었습니다!
    echo.
    echo 생성된 파일 위치: dist\ezSLauncher.exe
    echo.
    for %%A in ("dist\ezSLauncher.exe") do (
        echo 파일 크기: %%~zA bytes
    )
    echo.
    echo 주의사항:
    echo - Windows Defender가 차단할 수 있습니다 (신뢰할 수 있는 파일임)
    REM echo - 첫 실행 시 "자세한 정보"를 클릭하고 "실행"을 선택하세요
    REM echo - 바이러스 검사: https://www.virustotal.com 에서 확인 가능
    echo.
    )
    
    REM explorer /select,"dist\ezSLauncher.exe"
) else (
    echo [오류] EXE 파일을 찾을 수 없습니다.
    echo dist 폴더를 확인해주세요.
)

echo.
pause