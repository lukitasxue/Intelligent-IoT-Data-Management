$folder = "docs/analytics_api_contract/v1"

$files = @(
    "single_sensor_response.json",
    "multi_sensor_response.json",
    "no_alert_response.json",
    "error_response.json"
)

foreach ($file in $files) {
    Write-Host "`nChecking $file"

    $path = Join-Path $folder $file
    $json = Get-Content $path -Raw | ConvertFrom-Json

    if (
        $null -eq $json.status -or
        $null -eq $json.generated_at -or
        $null -eq $json.alerts -or
        $null -eq $json.summary -or
        $null -eq $json.errors
    ) {
        Write-Host "FAILED - Missing required response fields"
    }
    else {
        Write-Host "VALID - Response structure is correct"
    }
}

$single = Get-Content "$folder/single_sensor_response.json" -Raw | ConvertFrom-Json
$multi = Get-Content "$folder/multi_sensor_response.json" -Raw | ConvertFrom-Json
$noAlert = Get-Content "$folder/no_alert_response.json" -Raw | ConvertFrom-Json
$error = Get-Content "$folder/error_response.json" -Raw | ConvertFrom-Json

Write-Host "`nChecking alert types"

if ($single.alerts[0].alert_type -eq "POINTWISE_ANOMALY") {
    Write-Host "VALID - Single sensor alert type"
}
else {
    Write-Host "FAILED - Single sensor alert type"
}

if ($multi.alerts[0].alert_type -eq "CORRELATION_CHANGE") {
    Write-Host "VALID - Multi sensor alert type"
}
else {
    Write-Host "FAILED - Multi sensor alert type"
}

if ($noAlert.status -eq "success" -and $noAlert.summary.alert_count -eq 0) {
    Write-Host "VALID - No-alert response"
}
else {
    Write-Host "FAILED - No-alert response"
}

if ($error.status -eq "error" -and $error.errors.Count -gt 0) {
    Write-Host "VALID - Error response"
}
else {
    Write-Host "FAILED - Error response"
}
