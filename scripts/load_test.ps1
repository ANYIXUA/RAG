param(
    [ValidateSet("api", "cli")]
    [string]$Mode = "api",
    [string]$Url = "http://127.0.0.1:8000/query",
    [string[]]$Question = @(),
    [string]$QuestionsFile = "",
    [int]$Requests = 50,
    [int]$Concurrency = 5,
    [int]$Warmup = 3,
    [int]$TopK = 2,
    [double]$Timeout = 10,
    [string]$Output = "",
    [Nullable[double]]$FailOnErrorRate = $null,
    [Nullable[double]]$FailOnP95Ms = $null
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ($Question.Count -eq 0) {
    # Keep the default question ASCII-safe in the script file. It becomes
    # "光猫红灯咋办" at runtime.
    $Question = @(
        -join @(
            [char]0x5149,
            [char]0x732B,
            [char]0x7EA2,
            [char]0x706F,
            [char]0x548B,
            [char]0x529E
        )
    )
}

$argsList = @(
    "scripts/load_test.py",
    "--mode",
    $Mode,
    "--url",
    $Url,
    "--requests",
    "$Requests",
    "--concurrency",
    "$Concurrency",
    "--warmup",
    "$Warmup",
    "--top-k",
    "$TopK",
    "--timeout",
    "$Timeout"
)

foreach ($item in $Question) {
    if ($item -and $item.Trim()) {
        $argsList += @("--question", $item)
    }
}

if ($QuestionsFile -ne "") {
    $argsList += @("--questions-file", $QuestionsFile)
}

if ($Output -ne "") {
    $argsList += @("--output", $Output)
}

if ($null -ne $FailOnErrorRate) {
    $argsList += @("--fail-on-error-rate", "$FailOnErrorRate")
}

if ($null -ne $FailOnP95Ms) {
    $argsList += @("--fail-on-p95-ms", "$FailOnP95Ms")
}

python @argsList
