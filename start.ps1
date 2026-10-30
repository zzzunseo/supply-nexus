$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw '패키지 설치에 실패했습니다.' }
python launch_server.py
if ($LASTEXITCODE -ne 0) { throw '서버 시작에 실패했습니다. 오류 메시지를 확인해 주세요.' }
