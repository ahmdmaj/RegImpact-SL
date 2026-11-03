$headers = @{
    "Content-Type" = "application/json"
    "X-User-Role" = "sme_user"
}

$payload = @{
    profile = @{
        business_id = "BIZ-SL-FOOD-RETAIL-001"
        industry = "food_processing"
        activity = "food_manufacturing"
        employee_count = 12
        products = @(
            @{
                category = "biscuits_and_cookies"
                prepackaged = $true
            }
        )
        market = @{
            domestic = $true
            export_flag = $false
            b2b_only = $false
        }
        packaged_in_presence_of_purchaser = $false
        as_at_date = "2026-07-01"
    }
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod -Uri "http://localhost:8000/analysis" -Method Post -Headers $headers -Body $payload
$response | ConvertTo-Json -Depth 6 | Set-Content -Path "scratch\api_analysis_response.json" -Encoding UTF8

Write-Output "Status: Analysis completed successfully"
Write-Output "Total evaluated: $($response.total_rules_evaluated)"
Write-Output "Applicable: $($response.applicable_rules_count)"
Write-Output "Conditional: $($response.conditional_rules_count)"
Write-Output "Not applicable: $($response.not_applicable_rules_count)"
Write-Output "Unsupported: $($response.unsupported_rules_count)"
foreach ($ev in $response.evaluations) {
    Write-Output " - Rule: $($ev.rule_id) | Status: $($ev.status) | CoverageGap: $($ev.coverage_gap) | Doc: $($ev.document_title)"
}

