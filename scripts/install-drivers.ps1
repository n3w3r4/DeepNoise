# Installs the virtual audio cables DeepNoise uses (optional, run by the user):
#   - VB-CABLE        -> "CABLE Input/Output": DeepNoise's clean voice as a microphone for other apps
#   - VB-Audio Hi-Fi Cable -> "Hi-Fi Cable Input/Output": incoming call audio for "People talking to you"
#
# Both are made by VB-Audio Software (https://vb-audio.com) and are DONATIONWARE: free to use, but if you
# find them useful please pay a license at https://shop.vb-audio.com. They are downloaded from VB-Audio's
# official server, the digital signature is checked, and each installer asks for administrator rights.
#
#   powershell -ExecutionPolicy Bypass -File scripts\install-drivers.ps1

$ErrorActionPreference = 'Stop'
$work = Join-Path $env:TEMP 'DeepNoise-drivers'
New-Item -ItemType Directory -Force $work | Out-Null

$drivers = @(
    @{ Name = 'VB-CABLE (microfone virtual / virtual microphone)'
       Url  = 'https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip'
       Exe  = 'VBCABLE_Setup_x64.exe' },
    @{ Name = 'VB-Audio Hi-Fi Cable (som recebido / incoming audio)'
       Url  = 'https://download.vb-audio.com/Download_CABLE/HiFiCableAsioBridgeSetup_v1007.zip'
       Exe  = 'HiFiCableAsioBridgeSetup.exe' }
)
$trustedSigners = 'Vincent Burel|BUREL VINCENT'

Write-Host 'VB-CABLE e Hi-Fi Cable sao da VB-Audio Software (www.vb-cable.com) e sao donationware.' -ForegroundColor Cyan
Write-Host 'VB-CABLE and Hi-Fi Cable are by VB-Audio Software (www.vb-cable.com) and are donationware.' -ForegroundColor Cyan
Write-Host ''

foreach ($d in $drivers) {
    $answer = Read-Host "Instalar / install $($d.Name)? [S/n]"
    if ($answer -match '^(n|no|nao)$') { Write-Host '  pulado / skipped'; continue }

    $zip = Join-Path $work ([IO.Path]::GetFileName($d.Url))
    $dir = Join-Path $work ([IO.Path]::GetFileNameWithoutExtension($zip))
    Write-Host "  baixando $($d.Url)"
    Invoke-WebRequest -Uri $d.Url -OutFile $zip -UseBasicParsing
    if (Test-Path $dir) { Remove-Item $dir -Recurse -Force }
    Expand-Archive $zip -DestinationPath $dir

    $setup = Join-Path $dir $d.Exe
    $sig = Get-AuthenticodeSignature $setup
    if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch $trustedSigners) {
        throw "Assinatura inesperada em $($d.Exe): $($sig.Status) / $($sig.SignerCertificate.Subject). Nada foi instalado."
    }
    Write-Host "  assinatura ok: $($sig.SignerCertificate.Subject -replace ',.*','')"
    Write-Host '  abrindo o instalador (o Windows vai pedir permissao de administrador)...'
    Start-Process -FilePath $setup -Verb RunAs -Wait
}

Write-Host ''
Write-Host 'Pronto. Reinicie o PC para os cabos aparecerem. / Done. Restart Windows so the cables show up.' -ForegroundColor Green
