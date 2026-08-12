# Week 1 backup of deliverables (excludes data/raw re-downloadable HF dump)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$stamp = Get-Date -Format "yyyyMMdd"
$outDir = Join-Path $root "backups"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$archive = Join-Path $outDir "week1_$stamp.tar.gz"

# Prefer tar (Win10+)
$paths = @(
  "src",
  "docs",
  "status",
  "stats",
  "validators",
  "notes",
  "requirements.txt",
  "validate_day1.py",
  "validate_day2.py",
  "validate_day3.py",
  "validate_day4.py",
  "validate_day5.py",
  "validate_day6.py",
  "validate_day7.py",
  "validate_repo.py",
  "README.md",
  "data/gold",
  "data/processed",
  "data/extracted/metadata.jsonl",
  "checkpoints",
  "logs"
)

$existing = @()
foreach ($p in $paths) {
  if (Test-Path -LiteralPath $p) { $existing += $p }
}

if (Get-Command tar -ErrorAction SilentlyContinue) {
  & tar -czf $archive @existing
} else {
  $zip = $archive -replace "\.tar\.gz$", ".zip"
  if (Test-Path $zip) { Remove-Item $zip -Force }
  Compress-Archive -Path $existing -DestinationPath $zip -Force
  $archive = $zip
}

Write-Output "backup=$archive"
if (Test-Path $archive) {
  $len = (Get-Item $archive).Length
  Write-Output "size_bytes=$len"
}
