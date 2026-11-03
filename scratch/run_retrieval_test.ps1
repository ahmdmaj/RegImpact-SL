$output = Get-Content scratch\test_retrieval_live.py -Raw | docker exec -i regimpact-backend python -
Set-Content -Path scratch\retrieval_test_raw.txt -Value $output -Encoding UTF8
Write-Output "Retrieval test finished. Output lines: $($output.Length)"
