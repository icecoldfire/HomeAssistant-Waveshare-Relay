# PowerShell script to run ruff and mypy

Write-Host "Running ruff..."
ruff check --fix

Write-Host "Running mypy..."
mypy --explicit-package-bases .\custom_components