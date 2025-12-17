Write-Host "Cleaning up orphaned dev server processes..." -ForegroundColor Cyan

# Kill any processes using port 1420
$port1420 = Get-NetTCPConnection -LocalPort 1420 -ErrorAction SilentlyContinue
if ($port1420) {
    foreach ($conn in $port1420) {
        Write-Host "Killing process $($conn.OwningProcess) on port 1420..." -ForegroundColor Yellow
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

# Kill any Vite dev server processes
$viteProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*vite*"
}
if ($viteProcesses) {
    foreach ($proc in $viteProcesses) {
        Write-Host "Killing Vite process $($proc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}

# Kill any orphaned Tauri processes
$tauriProcesses = Get-Process -Name "qubes-gui*" -ErrorAction SilentlyContinue
if ($tauriProcesses) {
    foreach ($proc in $tauriProcesses) {
        Write-Host "Killing Tauri process $($proc.Id)..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Cleanup complete!" -ForegroundColor Green
Start-Sleep -Seconds 1
