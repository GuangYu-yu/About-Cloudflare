@echo on
setlocal enabledelayedexpansion

rem 确保有一个文件被拖放到脚本上
if "%~1"=="" (
    echo 请拖放一个文本文件到此脚本上。
    pause
    exit /b
)

rem 获取输入文件路径
set "inputFile=%~1"
rem 生成输出文件的路径
set "outputFile=%~dpn1_output.txt"

rem 设置 PowerShell 脚本的路径（在当前目录）
set "psScript=%~dp0split_cidr.ps1"

rem 创建 PowerShell 脚本内容
(
    echo param([string]$inputFile, [string]$outputFile)
    echo $cidrs = Get-Content -Path ^"%inputFile%^"
    echo $results = @()
    echo function Split-CIDR {
    echo     param([string]$cidr)
    echo     $cidrParts = $cidr -split '/' 
    echo     $ipAddress = [System.Net.IPAddress]::Parse($cidrParts[0])
    echo     $prefix = [int]$cidrParts[1]
    echo     $ipBytes = $ipAddress.GetAddressBytes()
    echo     if ($prefix -lt 31) {
    echo         $newPrefix = $prefix + 1
    echo         $subnetMask = [byte]((1 << (32 - $newPrefix)) - 1)
    echo         $ipBytes[3] = [byte]($ipBytes[3] -band -subnetMask - 1)
    echo         $firstIpBytes = [byte[]]$ipBytes.Clone()
    echo         $secondIpBytes = [byte[]]$ipBytes.Clone()
    echo         $firstIpBytes[3] = [byte]($ipBytes[3] -band -subnetMask)
    echo         $secondIpBytes[3] = [byte]($ipBytes[3] -band -subnetMask - 1 + 1)
    echo         $firstCidr = "$([System.Net.IPAddress]::new($firstIpBytes))/$newPrefix"
    echo         $secondCidr = "$([System.Net.IPAddress]::new($secondIpBytes))/$newPrefix"
    echo         return @($firstCidr, $secondCidr)
    echo     } else {
    echo         return @($cidr)
    echo     }
    echo }
    echo foreach ($cidr in $cidrs) {
    echo     if ($cidr -match "^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$") {
    echo         $cidr = $cidr.Trim()
    echo         $results += Split-CIDR -cidr $cidr
    echo     } else {
    echo         Write-Output "Invalid CIDR format: $cidr"
    echo     }
    echo }
    echo $results | Out-File -FilePath ^"%outputFile%^" -Encoding ASCII
) > "%psScript%"

rem 检查 PowerShell 脚本是否生成成功
if exist "%psScript%" (
    echo PowerShell 脚本生成成功: "%psScript%"
    echo PowerShell 脚本内容如下:
    type "%psScript%"
) else (
    echo PowerShell 脚本生成失败，路径: "%psScript%"
    pause
    exit /b
)

rem 调用 PowerShell 脚本处理文件
powershell -ExecutionPolicy Bypass -NoProfile -File "%psScript%" -inputFile "%inputFile%" -outputFile "%outputFile%"

rem 检查 PowerShell 脚本执行情况
if %errorlevel% neq 0 (
    echo 处理过程中发生错误。
) else (
    echo 处理完成。输出已保存到 %outputFile%。
)

rem 保持命令行窗口打开
pause
