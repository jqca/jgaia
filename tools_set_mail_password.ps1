# Set the mailbox password for info@jgaia.org into Railway (service: jgaia).
#
# Why this exists: the assistant is not allowed to handle passwords. The CEO
# types it here; the value goes straight to Railway and is never shown, logged,
# or written anywhere else. The temp file is UTF-8 without BOM on purpose -
# a BOM travels into the variable and breaks SMTP auth invisibly
# (measured 2026-08-04 with INQUIRY_ADMIN_TOKEN).
$ErrorActionPreference = 'Stop'

$railway = Join-Path $env:APPDATA 'npm\railway.cmd'
if (-not (Test-Path $railway)) { Write-Host '  railway CLI not found.'; exit 1 }

$sec = Read-Host -AsSecureString '  password'
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
if ([string]::IsNullOrWhiteSpace($plain)) { Write-Host '  empty - aborted.'; exit 1 }

$tmp = Join-Path $env:TEMP ('sm_' + [guid]::NewGuid().ToString('N') + '.txt')
try {
    [IO.File]::WriteAllText($tmp, $plain, (New-Object Text.UTF8Encoding($false)))
    $plain = $null
    $out = & cmd /c "type `"$tmp`" | `"$railway`" variables --service jgaia --set-from-stdin SMTP_PASSWORD" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  failed: $out"
        exit 1
    }
    Write-Host '  saved.'
} finally {
    if (Test-Path $tmp) { Remove-Item $tmp -Force }
}

# Show only whether it landed, never the value.
$kv = & $railway variables --service jgaia --kv 2>$null
$row = ($kv | Select-String -Pattern '^SMTP_PASSWORD=' | Select-Object -First 1)
if ($row) {
    $val = ($row.ToString() -split '=', 2)[1]
    $bytes = [Text.Encoding]::UTF8.GetBytes($val)
    $nonAscii = @($bytes | Where-Object { $_ -gt 127 }).Count
    Write-Host "  stored: $($val.Length) chars, non-ascii bytes: $nonAscii (0 is correct)"
} else {
    Write-Host '  WARNING: not found after saving.'
}
