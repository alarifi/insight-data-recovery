@echo off
title Insight Data Recovery Studio Pro
chcp 65001 >nul
cd /d "%~dp0InsightDataRecovery"
start "" pythonw main.py
exit

