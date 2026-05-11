param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $Args
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$kaggle = Join-Path $root ".venv-kaggle\Scripts\kaggle.exe"

if (-not (Test-Path $kaggle)) {
    throw "Kaggle CLI not found at $kaggle. Recreate it with: py -3.11 -m venv .venv-kaggle; .\.venv-kaggle\Scripts\python -m pip install git+https://github.com/Kaggle/kaggle-cli.git"
}

& $kaggle @Args
