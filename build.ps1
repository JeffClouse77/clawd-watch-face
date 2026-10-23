<#
.SYNOPSIS
    Builds, signs and (optionally) installs the Clawd watch face APK.

.DESCRIPTION
    Watch Face Format packages have no Java code, so the build is just:
      1. aapt2 compile   -> flat resource files
      2. aapt2 link      -> unsigned APK (manifest + resources)
      3. zipalign        -> 4-byte aligned APK
      4. apksigner       -> signed with a local debug keystore
      5. adb install -r  -> onto the watch (if -Install)

.PARAMETER Install
    Push the signed APK to the watch over adb after building.
.PARAMETER Device
    adb serial (ip:port for wireless debugging). Default: first connected device.

.EXAMPLE
    .\build.ps1 -Install -Device 192.168.1.50:43395
#>
[CmdletBinding()]
param(
    [switch]$Install,
    [string]$Device
)

$ErrorActionPreference = 'Stop'
$root      = $PSScriptRoot
$sdk       = 'C:\Android\Sdk'
$bt        = "$sdk\build-tools\35.0.0"
$androidJar= "$sdk\platforms\android-34\android.jar"
$jdk       = 'C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot'
$adb       = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe"
$out       = "$root\build"
$keystore  = "$root\debug.keystore"
$ksPass    = if ($env:CLAWD_KS_PASS) { $env:CLAWD_KS_PASS } else { 'changeit' }   # set CLAWD_KS_PASS for your own key

$env:JAVA_HOME = $jdk
$env:Path = "$jdk\bin;$env:Path"

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

# --- clean -----------------------------------------------------------------
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Force "$out\compiled" | Out-Null

# --- 1. compile resources --------------------------------------------------
Step 'aapt2 compile'
& "$bt\aapt2.exe" compile --dir "$root\res" -o "$out\compiled\res.zip"
if ($LASTEXITCODE) { throw "aapt2 compile failed ($LASTEXITCODE)" }

# --- 2. link ---------------------------------------------------------------
Step 'aapt2 link'
& "$bt\aapt2.exe" link `
    -o "$out\clawd-unsigned.apk" `
    -I $androidJar `
    --manifest "$root\AndroidManifest.xml" `
    --min-sdk-version 33 --target-sdk-version 34 `
    --version-code 1 --version-name 1.0 `
    "$out\compiled\res.zip"
if ($LASTEXITCODE) { throw "aapt2 link failed ($LASTEXITCODE)" }

# --- 3. zipalign -----------------------------------------------------------
Step 'zipalign'
& "$bt\zipalign.exe" -f -p 4 "$out\clawd-unsigned.apk" "$out\clawd-aligned.apk"
if ($LASTEXITCODE) { throw "zipalign failed ($LASTEXITCODE)" }

# --- 4. sign ---------------------------------------------------------------
if (-not (Test-Path $keystore)) {
    Step 'creating debug keystore (one time)'
    & "$jdk\bin\keytool.exe" -genkeypair -v -keystore $keystore -storepass $ksPass -keypass $ksPass `
        -alias clawd -keyalg RSA -keysize 2048 -validity 10000 `
        -dname 'CN=Clawd Watch Face, O=Redline Tech Solutions, C=US' | Out-Null
    if ($LASTEXITCODE) { throw "keytool failed ($LASTEXITCODE)" }
}
Step 'apksigner'
& "$bt\apksigner.bat" sign --ks $keystore --ks-pass pass:$ksPass --key-pass pass:$ksPass `
    --ks-key-alias clawd --out "$out\clawd.apk" "$out\clawd-aligned.apk"
if ($LASTEXITCODE) { throw "apksigner failed ($LASTEXITCODE)" }
& "$bt\apksigner.bat" verify --print-certs "$out\clawd.apk" | Select-Object -First 2
Write-Host "Built: $out\clawd.apk ($([math]::Round((Get-Item "$out\clawd.apk").Length/1KB)) KB)" -ForegroundColor Green

# --- 5. install ------------------------------------------------------------
if ($Install) {
    $s = @(); if ($Device) { $s = @('-s', $Device) }
    Step 'adb install'
    & $adb @s install -r "$out\clawd.apk"
    if ($LASTEXITCODE) { throw "adb install failed ($LASTEXITCODE)" }
}
