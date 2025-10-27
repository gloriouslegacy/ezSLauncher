@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo 아이콘 캐시 정리 도구
echo ========================================
echo.
echo 이 스크립트는 Windows 아이콘 캐시를 지웁니다.
echo EXE 파일의 아이콘이 보이지 않을 때 사용하세요.
echo.
pause

echo.
echo 작업 중...
echo.

REM 탐색기 프로세스 종료
echo [1/5] 탐색기 종료 중...
taskkill /f /im explorer.exe >nul 2>&1

REM 아이콘 캐시 삭제
echo [2/5] 아이콘 캐시 삭제 중...
del /f /s /q /a "%localappdata%\IconCache.db" >nul 2>&1
del /f /s /q /a "%localappdata%\Microsoft\Windows\Explorer\iconcache*.db" >nul 2>&1
del /f /s /q /a "%localappdata%\Microsoft\Windows\Explorer\thumbcache*.db" >nul 2>&1

REM 축소판 그림 캐시 삭제
echo [3/5] 축소판 캐시 삭제 중...
del /f /s /q /a "%localappdata%\Microsoft\Windows\Explorer\*.db" >nul 2>&1

REM 아이콘 캐시 새로 고침
echo [4/5] 아이콘 캐시 새로 고침...
ie4uinit.exe -show >nul 2>&1

REM 탐색기 재시작
echo [5/5] 탐색기 재시작 중...
start explorer.exe

echo.
echo ========================================
echo 완료!
echo ========================================
echo.
echo 아이콘 캐시가 정리되었습니다.
echo 이제 EXE 파일의 아이콘이 정상적으로 보일 것입니다.
echo.
echo 만약 여전히 보이지 않는다면:
echo 1. 컴퓨터를 재부팅하세요
echo 2. 아이콘 파일(.ico)이 올바른 형식인지 확인하세요
echo 3. PyInstaller를 다시 실행하여 EXE를 재빌드하세요
echo.
pause
