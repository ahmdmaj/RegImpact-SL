$output = Get-Content scratch\audit_corpus_phase_5_4.py -Raw | docker exec -i regimpact-backend python -
Set-Content -Path scratch\corpus_audit_raw.txt -Value $output -Encoding UTF8
Write-Output "Audit finished. Output length: $($output.Length)"
