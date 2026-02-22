# Clear existing file if present
if (Test-Path codebase.txt) { Remove-Item codebase.txt }

# Find all .py and .qss files
Get-ChildItem -Recurse -Include *.py, *.qss | ForEach-Object {
    "================================================================================" | Out-File -FilePath codebase.txt -Append
    "FILE: $($_.FullName)" | Out-File -FilePath codebase.txt -Append
    "================================================================================" | Out-File -FilePath codebase.txt -Append
    Get-Content $_.FullName | Out-File -FilePath codebase.txt -Append
    "`r`n`r`n" | Out-File -FilePath codebase.txt -Append
}

Write-Host "Created codebase.txt with $(Get-Content codebase.txt | Select-String "FILE:" | Measure-Object | %{$_.Count}) files"