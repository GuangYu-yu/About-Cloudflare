@echo off
setlocal enabledelayedexpansion

for %%f in (%*) do (
    (for /f "delims=" %%a in (%%f) do (
        for /f "delims=/" %%b in ("%%a") do (
            echo %%b
        ))
    ) > "%%~dpnf_processed.txt"
)

endlocal