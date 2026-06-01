@echo off
setlocal enabledelayedexpansion

:: 检查是否有文件作为参数传递
if "%1"=="" (
    echo Please drag and drop the text file onto this batch file.
    exit /b
)

:: 读取文件名，不包含扩展名
set "filename=%~n1"

:: 创建临时文件来存储修改后的内容
set "tempfile=%temp%\%filename%.tmp"

:: 读取原文件的每一行，并进行处理
for /f "tokens=* delims=" %%a in (%1) do (
    set "line=%%a"
    :: 替换域名或IP地址
    set "modified1=!line!:443#!line!1111d"
    set "modified2=!line!:8443#!line!8443d"
    set "modified3=!line!:2053#!line!2053d"
    set "modified4=!line!:2083#!line!2083d"
    set "modified5=!line!:2087#!line!2087d"
    set "modified6=!line!:2096#!line!2096d"

    :: 将修改后的行写入临时文件
    echo !modified1! >> !tempfile!
    echo !modified2! >> !tempfile!
    echo !modified3! >> !tempfile!
    echo !modified4! >> !tempfile!
    echo !modified5! >> !tempfile!
    echo !modified6! >> !tempfile!
)

:: 替换原文件
move /y !tempfile! %1

:: 清理临时文件
del !tempfile!

echo Done.
endlocal