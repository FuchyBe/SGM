@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set VERSION=0.7
echo === SGM - Statics ^& GSX Manager : creation du paquet portable (beta v%VERSION%) ===
echo.

for %%F in (statics_manager.py i18n.py README.md README_FR.md licenses\LICENSE-SGM.txt licenses\THIRD-PARTY-NOTICES.txt licenses\LGPL-3.0-only.txt licenses\GPL-3.0-only.txt) do (
  if not exist "%%F" ( echo Fichier manquant : %%F & pause & exit /b 1 )
)

python --version >nul 2>&1 || (
  echo Python n'est pas installe. Installe-le depuis https://www.python.org/downloads/
  echo en cochant "Add python.exe to PATH", puis relance ce fichier.
  pause
  exit /b 1
)

python -m pip install --upgrade pyside6 pyinstaller || ( pause & exit /b 1 )

rem --onedir : les bibliotheques Qt / PySide6 restent des fichiers separes et remplacables (exigence LGPL)
python -m PyInstaller --noconfirm --clean --onedir --windowed --name "SGM" statics_manager.py || ( pause & exit /b 1 )

rem Licences, README
xcopy /E /I /Y licenses "dist\SGM\licenses" >nul
for /f "delims=" %%P in ('python -c "import sys,os;print(os.path.join(sys.base_prefix,'LICENSE.txt'))"') do set PYLIC=%%P
if exist "%PYLIC%" ( copy /Y "%PYLIC%" "dist\SGM\licenses\Python-PSF-LICENSE.txt" >nul )
copy /Y README.md "dist\SGM\README.md" >nul
copy /Y README_FR.md "dist\SGM\README_FR.md" >nul

rem Archive prete a publier
powershell -NoProfile -Command "Compress-Archive -Path 'dist\SGM' -DestinationPath 'dist\SGM_beta_v%VERSION%.zip' -Force"

echo.
echo Termine :
echo   - application : dist\SGM\SGM.exe   (garder tout le dossier dist\SGM)
echo   - archive a publier : dist\SGM_beta_v%VERSION%.zip
echo.
echo Application portable : copie le dossier SGM ou tu veux. Ses reglages et
echo sauvegardes seront ranges dans "SGM_data", dans ce dossier.
pause
