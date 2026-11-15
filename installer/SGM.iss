; Installeur de SGM (Inno Setup 6) — décision de Fabian du 2026-11-15 (docs/DECISIONS.md).
; Installation pour l'utilisateur seul, sans demande administrateur : %LOCALAPPDATA%\Programs\SGM.
; Les données (réglages, sauvegardes, états d'origine) sont dans %APPDATA%\SGM, gardées à la désinstallation
; sauf si l'utilisateur demande de les supprimer.
; Compilation : iscc /DAppVersion=1.0 /DSourceDir=..\dist\SGM installer\SGM.iss

#ifndef AppVersion
  #define AppVersion "0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\SGM"
#endif

[Setup]
; même identifiant que INSTALL_APP_ID dans statics_manager.py (la mise à jour automatique met à jour sa version)
AppId={{6F1C2B7E-5A43-4D2B-9C1E-7B3F0A9D4E21}
AppName=SGM - Statics & GSX Manager
AppVersion={#AppVersion}
AppVerName=SGM {#AppVersion}
AppPublisher=Fabian Fuchs
AppPublisherURL=https://github.com/FuchyBe/SGM
AppSupportURL=https://github.com/FuchyBe/SGM/issues
AppUpdatesURL=https://github.com/FuchyBe/SGM/releases
DefaultDirName={localappdata}\Programs\SGM
DefaultGroupName=SGM
DisableProgramGroupPage=yes
; emplacement fixe : la désinstallation efface tout le dossier du programme, il ne doit jamais être un dossier
; choisi par l'utilisateur (C:\Jeux…)
DisableDirPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=SGM_Setup_v{#AppVersion}
SetupIconFile=..\assets\SGM.ico
UninstallDisplayIcon={app}\SGM.exe
UninstallDisplayName=SGM - Statics & GSX Manager
LicenseFile=..\licenses\LICENSE-SGM.txt
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#AppVersion}

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "pt"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "nl"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "pl"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
en.DeleteData=Also delete SGM's data (settings, statics profiles, backups and the original state of your sceneries)?%n%nChoose No to keep them for a later reinstall.
fr.DeleteData=Supprimer aussi les données de SGM (réglages, profils de statics, sauvegardes et état d'origine de tes scènes) ?%n%nChoisis Non pour les garder en vue d'une réinstallation.
de.DeleteData=Auch die SGM-Daten löschen (Einstellungen, Statics-Profile, Sicherungen und Originalzustand deiner Szenerien)?%n%nWähle Nein, um sie für eine spätere Neuinstallation zu behalten.
es.DeleteData=¿Eliminar también los datos de SGM (ajustes, perfiles de statics, copias de seguridad y estado original de tus escenarios)?%n%nElige No para conservarlos para una reinstalación.
it.DeleteData=Eliminare anche i dati di SGM (impostazioni, profili degli statics, backup e stato originale dei tuoi scenari)?%n%nScegli No per conservarli per una reinstallazione.
pt.DeleteData=Eliminar também os dados do SGM (definições, perfis de statics, cópias de segurança e estado original dos seus cenários)?%n%nEscolha Não para os manter para uma reinstalação.
nl.DeleteData=Ook de gegevens van SGM verwijderen (instellingen, statics-profielen, back-ups en oorspronkelijke toestand van je scenery's)?%n%nKies Nee om ze te bewaren voor een latere herinstallatie.
pl.DeleteData=Usunąć też dane SGM (ustawienia, profile statics, kopie zapasowe i stan oryginalny scenerii)?%n%nWybierz Nie, aby zachować je na wypadek ponownej instalacji.
ru.DeleteData=Удалить также данные SGM (настройки, профили statics, резервные копии и исходное состояние сценариев)?%n%nВыберите «Нет», чтобы сохранить их для повторной установки.
ja.DeleteData=SGM のデータ（設定、statics プロファイル、バックアップ、シーナリーの元の状態）も削除しますか？%n%n再インストールに備えて残す場合は「いいえ」を選んでください。

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "SGM_data\*"
Source: "SGM.installed"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\SGM - Statics & GSX Manager"; Filename: "{app}\SGM.exe"
Name: "{userdesktop}\SGM - Statics & GSX Manager"; Filename: "{app}\SGM.exe"; Tasks: desktopicon

[Run]
; Lancé par l'Explorateur, comme depuis le menu Démarrer : lancé directement par l'installeur (processus enfant
; qui se ferme), SGM restait figé au premier démarrage (constaté par Fabian le 2026-11-15).
Filename: "{win}\explorer.exe"; Parameters: """{app}\SGM.exe"""; Description: "{cm:LaunchProgram,SGM}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; fichiers ajoutés par la mise à jour automatique (le dossier du programme seulement, jamais les données)
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  { Données gardées par défaut ; suppression seulement sur demande explicite (bouton par défaut : Non) }
  if (CurUninstallStep = usPostUninstall) and not UninstallSilent then
    if MsgBox(CustomMessage('DeleteData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{userappdata}\SGM'), True, True, True);
end;
