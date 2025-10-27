# 파일명: git_push.ps1 (수정 버전: git.exe 명시적 호출)
# 실행 예시: .\git_push.ps1 "commit-message"

param(
    [Parameter(Mandatory=$true)]
    [string]$commit_message
)

# 1. 모든 변경 사항 스테이징
Write-Host "✅ git add . 실행 중..."
git.exe add .

# 2. 커밋 실행 (오류 발생 시 push 중단)
Write-Host "✅ git commit -m ""$commit_message"" 실행 중..."
try {
    # git 대신 git.exe를 명시적으로 호출하여 오류 회피
    git.exe commit -m "$commit_message" -ErrorAction Stop
    
}
catch {
    # Git 커밋 실패 시 실행되는 블록 (변경 사항이 없을 때도 여기에 들어옵니다)
    Write-Host "-----------------------------------"
    Write-Host "❌ Git 커밋 실패: 변경 사항이 없거나 다른 문제가 발생했습니다." -ForegroundColor Red
    # 상세 메시지를 좀 더 깔끔하게 처리
    $errorMessage = $_.Exception.Message -replace "(?m)^error: ", "" | Out-String | Select-Object -First 1
    Write-Host "상세: $($errorMessage.Trim())" -ForegroundColor Yellow
    Write-Host "-----------------------------------"
    
    # Git 커밋 실패 후 스크립트 종료 (push 방지)
    exit 1
}

# 3. 푸시 실행 (커밋이 성공했을 때만 실행됨)
Write-Host "✅ git push origin main 실행 중..."
git.exe push origin main

# 4. 결과 출력
Write-Host "-----------------------------------"
Write-Host "🎉 Git 자동화 완료!" -ForegroundColor Green
Write-Host "커밋 메시지: $commit_message"
Write-Host "-----------------------------------"