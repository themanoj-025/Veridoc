# Restart Docker Desktop
Write-Host "Stopping Docker Desktop processes..."
Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Killed PID $($_.Id)"
}

Write-Host "Waiting 5 seconds..."
Start-Sleep -Seconds 5

Write-Host "Starting Docker Desktop..."
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Write-Host "Docker Desktop launched - waiting 45 seconds for daemon..."
