$ErrorActionPreference='Stop'
$cuRoot=Split-Path -Parent $PSScriptRoot
$cuSid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User
$cuSystem=New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
foreach ($cuName in @('.env','.migration.env','.report-demo.env')) {
    $cuPath=Join-Path $cuRoot $cuName
    if (Test-Path -LiteralPath $cuPath) {
        & icacls.exe $cuPath /inheritance:r /grant:r (('*' + $cuSid.Value) + ':(F)') '*S-1-5-18:(F)' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not restrict $cuName" }
        Write-Output "Restricted local file access: $cuName"
    }
}
