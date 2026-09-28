@echo 

	setlocal EnableExtensions EnableDelayedExpansion

	if not "%~1"=="hidden" (
	start /min "" cmd /c ""%~f0" hidden"
	exit /b
	)

rem Куда сохранять бэкап/Where to save backup
	set "BACKUP_PATH=C:\Users\Scane\AppData\Roaming\Nitrox\saves"

rem Краткое имя игры или приложения/The short name of the game or application
	set "NAME=Subna"

rem Что сохранять/What to save
	set "SOURCE_FOLDER=C:\Users\Scane\AppData\Roaming\7DaysToDie\Saves\BackUp\BackUps"

rem Путь к вин рару (я его кинул в комплект)/The way to the vintage (I threw it in the kit)
	set "WINRAR=C:\Program Files\WinRAR\WinRAR.exe"

rem Имя процесса игры в диспетчере задач / Game process name in Task Manager
	set "GAME_PROCESS=Nitrox.Launcher.exe"

rem Как часто проверять, запущена ли игра (в секундах) / How often to check if game is running
	set "CHECK_INTERVAL=10"

rem Как часто делать обычный бэкап при запущенной игре (в секундах) / How often to make a regular backup when the game is running (in seconds)
	set "BACKUP_INTERVAL=10"

rem Сколько проверок по 10 секунд в одном интервале бэкапа / How many 10s checks per backup interval
	set /a "TICKS_PER_BACKUP=BACKUP_INTERVAL / CHECK_INTERVAL"


rem Пока игра не запущена - раз в 10 секунд просто проверяем процесс/While the game is not running, we just check the process every 10 seconds.
	goto wait_game

	:wait_game
rem Ждём, пока игра запустится/We are waiting for the game to start
	tasklist /FI "IMAGENAME eq %GAME_PROCESS%" | find /I "%GAME_PROCESS%" >nul
	if errorlevel 1 (
	timeout /t %CHECK_INTERVAL% /nobreak >nul
	goto wait_game
	)

rem Игра запущена — сбрасываем счётчик и запускаем цикл ожидания первого бэкапа/The game is running — we reset the counter and start the cycle of waiting for the first backup.
	set /a tick=0
	goto session_loop


	:session_loop
	rem Проверяем, не закрылась ли игра/Checking to see if the game has closed.
	tasklist /FI "IMAGENAME eq %GAME_PROCESS%" | find /I "%GAME_PROCESS%" >nul
	if errorlevel 1 goto final_backup

rem Увеличиваем счётчик каждые 10 секунд/We increase the counter every 10 seconds
	set /a tick+=1

rem Если прошло количество секунд которое указанно - делаем бэкап/If the specified number of seconds has passed, we make a backup.
	if %tick% GEQ %TICKS_PER_BACKUP% (
	set /a tick=0
	call :MakeBackup L
	)

	timeout /t %CHECK_INTERVAL% /nobreak >nul
	goto session_loop


	:final_backup
rem Игра закрылась — делаем последний бэкап с префиксом C-/The game is closed — we are making the last backup with the prefix C-
	call :MakeBackup C
	exit /b


	:MakeBackup
rem %1 = префикс (S или C)/%1 = prefix (S or C)
	set "prefix=%~1"

	if not exist "%BACKUP_PATH%" mkdir "%BACKUP_PATH%"

	set "ts="
	for /l %%r in (1,1,3) do (
	if not defined ts for /f %%i in ('
		powershell -NoProfile -Command "(Get-Date).ToString(\"yyyy-MM-dd-HH-mm-ss\")"
	') do set "ts=%%i"
	if not defined ts timeout /t 1 /nobreak >nul
	)
if not defined ts set "ts=fallback_!RANDOM!"

set "archive_name=%prefix%-%NAME%_%ts%"

rem Создаем архив в фоне с сжатием / Create archive in background with compression
start "" "%WINRAR%" a -r -ep1 -m5 -ibck -idc -y "%BACKUP_PATH%\!archive_name!.rar" "%SOURCE_FOLDER%\*"

exit /b
	

rem 		   ------------------------------ТИТРЫ---------------------------------
rem 		   -------------------В создании принимали участиЕ--------------------
rem 		   --------------------------Dfyz - кодер №1---------------------------
rem 		   --------------самый умный человек которого я знаю-----------------
rem 		   ------------------------Deep Seek - кодер №2-----------------------
rem 		   --------------------------Cursor - кодер №3-------------------------
rem 		   ----------------------------------и----------------------------------
rem 		   --------------------------------ДимоН-------------------------------
rem 		   --------------------------------Он жЕ-------------------------------
rem 		   --------------------------------ScanE-------------------------------
rem 		   --------------------------------Он жЕ-------------------------------
rem 		   --------------------------Писатель комментоВ-----------------------
rem 		   --------------------------------Он жЕ-------------------------------
rem 		   ---------------Человек который обожает помогать людяМ------------
rem 		   ---------------------№2 и №3 всегда к вашим усугаМ---------------
rem 		   ----------------------Dfyz -скорее всего очень устал----------------
rem 		   -------------------------но ждет меня чтобы помочь-----------------
rem 		   ----------------А вот Димон наверное опять где-то валяетсЯ--------
rem 		   ---------------И забил большой и длинный *** на свою работУ------

rem 		--------------------------------TITLES-----------------------------------
rem 		----------------The following people participated in creation:---------------
rem 		----------------------------Dfyz - coder №1------------------------------
rem 		------------------------the smartest person I know------------------------
rem 		--------------------------Deep Seek - coder №2--------------------------
rem 		---------------------------Cursor - coder №3-----------------------------
rem 		--------------------------------and--------------------------------------
rem 		-------------------------------Dimon-------------------------------------
rem 		--------------------------------He's--------------------------------------
rem 		-------------------------------ScanE-------------------------------------
rem 		--------------------------------He's--------------------------------------
rem 		-------------------------Writer of Comments------------------------------
rem 		--------------------------------He's--------------------------------------
rem 		-------------------A person who loves helping people----------------------
rem 		----------------№2 and №3 are always at your service--------------------
rem 		----------------------Dfyz - probably very tired---------------------------
rem 		----------------------but waiting for me to help---------------------------
rem 		------------But Dimon is probably lying around somewhere again------------
rem 		---------------And scored a big and long *** on his job--------------------
