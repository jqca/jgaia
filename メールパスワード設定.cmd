@echo off
title JGAIA メール送信パスワードの設定
echo.
echo   info@jgaia.org のメールパスワードを設定します。
echo   入力した文字は画面に表示されません。
echo   値はこのPCからRailwayへ直接送られ、どこにも保存されません。
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools_set_mail_password.ps1"
echo.
echo   終わったら Claude に「入れた」とだけ伝えてください。
echo.
pause
