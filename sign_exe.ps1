<#
.SYNOPSIS
  Sign Jarvis exe with a self-signed code-signing certificate (dev/demo).

.DESCRIPTION
  Creates (or reuses) a self-signed code signing certificate and signs
  Jarvis.exe and the installer with a timestamp.

  TRUST NOTE:
   - A self-signed signature does NOT remove the SmartScreen warning for other
     users. It guarantees integrity and is treated as trusted only on machines
     where this certificate was imported (see the Trust block printed below).
   - For public distribution use a CA certificate (paid) or free options for
     open source: SignPath.io, Azure Trusted Signing.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File sign_exe.ps1
#>

$ErrorActionPreference = "Stop"
$subject = "CN=Jarvis Dev (lastlofty)"
$timestamp = "http://timestamp.digicert.com"

# 1) Reuse existing certificate or create a new one
$cert = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { $_.Subject -eq $subject -and $_.HasPrivateKey } |
    Select-Object -First 1

if (-not $cert) {
    Write-Host "Creating self-signed certificate..." -ForegroundColor Cyan
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $subject `
        -CertStoreLocation Cert:\CurrentUser\My `
        -KeyUsage DigitalSignature `
        -KeyExportPolicy Exportable `
        -NotAfter (Get-Date).AddYears(3)
    Write-Host "Created certificate: $($cert.Thumbprint)" -ForegroundColor Green
} else {
    Write-Host "Using existing certificate: $($cert.Thumbprint)" -ForegroundColor Green
}

# 2) Files to sign
$targets = @("dist\Jarvis\Jarvis.exe")
$installers = Get-ChildItem "installer_out\*.exe" -ErrorAction SilentlyContinue
if ($installers) { $targets += ($installers | ForEach-Object { $_.FullName }) }

foreach ($file in $targets) {
    if (Test-Path $file) {
        Write-Host "Signing: $file" -ForegroundColor Cyan
        $res = Set-AuthenticodeSignature -FilePath $file -Certificate $cert -TimestampServer $timestamp
        Write-Host ("  -> " + $res.Status) -ForegroundColor Yellow
    } else {
        Write-Host "Skip (not found): $file" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "Done. Verify with: Get-AuthenticodeSignature <path>" -ForegroundColor Green
Write-Host "To make it trusted on THIS machine, import the cert into Root + TrustedPublisher:" -ForegroundColor DarkCyan
Write-Host "  Export-Certificate -Cert (Get-ChildItem Cert:\CurrentUser\My | ? Subject -eq '$subject') -FilePath jarvis-dev.cer" -ForegroundColor DarkGray
Write-Host "  Import-Certificate -FilePath jarvis-dev.cer -CertStoreLocation Cert:\CurrentUser\Root" -ForegroundColor DarkGray
Write-Host "  Import-Certificate -FilePath jarvis-dev.cer -CertStoreLocation Cert:\CurrentUser\TrustedPublisher" -ForegroundColor DarkGray
