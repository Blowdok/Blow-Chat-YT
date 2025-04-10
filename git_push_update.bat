@echo off
REM Script pour ajouter, commit et push les modifications vers GitHub

:: === DEMANDE DU MESSAGE DE COMMIT ===
set /p COMMIT_MESSAGE=Message du commit :

:: === AJOUT, COMMIT ET PUSH ===
git add .
git commit -m "%COMMIT_MESSAGE%"
git push

echo.
echo ✅ Modifications poussées avec succès vers GitHub.
pause
