$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
& (Join-Path $PSScriptRoot '.venv\Scripts\waitress-serve.exe') --listen=127.0.0.1:5000 app:app
