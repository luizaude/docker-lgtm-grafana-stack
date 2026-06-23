Param(
  [int]$Count = 100,
  [string]$BaseUrl = "http://localhost:8080",
  [double]$SleepSeconds = 0.5
)

$endpoints = @("users", "orders", "slow", "error")

for ($i = 1; $i -le $Count; $i++) {
  $endpoint = Get-Random -InputObject $endpoints
  try {
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/$endpoint" | Out-Null
  } catch {
    # ignore errors (we want errors to appear in telemetry too)
  }
  Start-Sleep -Seconds $SleepSeconds
}

Write-Output "Done: $Count requests to $BaseUrl"
