Set-Location "c:\Users\LENOVO\OneDrive\Desktop\mypy tutor"

Write-Host "Splitting frontend-react subtree..." -ForegroundColor Cyan
git subtree split --prefix=frontend-react -b frontend-deploy
if ($LASTEXITCODE -ne 0) { Write-Host "Subtree split failed" -ForegroundColor Red; exit 1 }

Write-Host "Force-pushing to frontend repo..." -ForegroundColor Cyan
git push frontend frontend-deploy:main --force
if ($LASTEXITCODE -ne 0) { Write-Host "Push failed" -ForegroundColor Red; exit 1 }

Write-Host "Cleaning up temp branch..." -ForegroundColor Cyan
git branch -D frontend-deploy

Write-Host "FRONTEND_PUSH_DONE - Vercel will now trigger a build" -ForegroundColor Green
