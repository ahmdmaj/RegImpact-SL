$lines = Get-Content -Path 'C:\Users\HP\.gemini\antigravity\brain\dc459a64-371a-4d21-b70d-b30f9efae5bb\.system_generated\logs\transcript_full.jsonl'
for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    if ($lines[$i] -match '"type":"USER_INPUT"') {
        $obj = ConvertFrom-Json $lines[$i]
        Set-Content -Path 'scratch/phase_5_4_prompt.txt' -Value $obj.content -Encoding UTF8
        Write-Output "Found prompt at line $i, length: $($obj.content.Length)"
        break
    }
}
