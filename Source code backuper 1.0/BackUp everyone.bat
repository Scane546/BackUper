@echo off

	setlocal EnableExtensions EnableDelayedExpansion

rem Куда сохранять бэкап/Where to save backup
	set "BACKUP_PATH=C:\Users\Scane\AppData\Roaming\Nitrox\saves"

rem Краткое имя игры или приложения/The short name of the game or application
	set "NAME=Subna"

rem Что сохранять/What to save
	set "SOURCE_FOLDER=C:\Users\Scane\AppData\Roaming\7DaysToDie\Saves\BackUp\BackUps"

rem Путь к винрару (я его кинул в комплект)/Path to WinRAR (I put it in the package)
	set "WINRAR=C:\Program Files\WinRAR\WinRAR.exe"

rem Создать папку бэкапа, если она не существует/Create a backup folder if it doesn't exist
	if not exist "%BACKUP_PATH%" mkdir "%BACKUP_PATH%"

rem Создать имя архива с датой и временем (месяц-день_часы;минуты;секунды) / Create archive name with date and time (month-day_hour;minute;second)
	set "ts="
	for /l %%r in (1,1,3) do (
		if not defined ts for /f %%i in ('
			powershell -NoProfile -Command "$d=Get-Date; $d.ToString(\"yyyy-MM-dd\")+\"_\"+$d.ToString(\"HH\")+\";\"+$d.ToString(\"mm\")+\";\"+$d.ToString(\"ss\")"
		') do set "ts=%%i"
		if not defined ts timeout /t 1 /nobreak >nul
	)
	if not defined ts set "ts=fallback_!RANDOM!"
	set "archive_name=S-%NAME%_!ts!"

rem Создать архив в фоне со сжатием (от m5 до m0, где m0 почти не сжимается, а m5 сжимет максимально) / Create an archive in the background with compression (from m5 to m0, where m0 is almost uncompressed and m5 is compressed as much as possible)
	start "" "%WINRAR%" a -r -ep1 -m5 -ibck -idc -y "%BACKUP_PATH%\!archive_name!.rar" "%SOURCE_FOLDER%\*"

rem a - добавить в архив (Add)/Add to Archive (Add)
rem Это главная команда для создания нового архива. Она указывает WinRAR добавлять файлы в архив./This is the main command for creating a new archive. It tells WinRAR to add files to the archive.

rem -r - рекурсивный обход (Recursive)/Recursive traversal
rem Обрабатывает все вложенные папки и файлы внутри указанной папки/Processes all subfolders and files inside the specified folder
rem Без этого параметра WinRAR добавил бы только файлы из корня %SOURCE_FOLDER%, но не из вложенных папок/Without this parameter, WinRAR would have added only files from the %SOURCE_FOLDER% root, but not from subfolders

rem -ep1 - исключить базовый путь (Exclude Path)/Exclude the base path (Exclude Path)
rem Этот параметр управляет тем, как пути сохраняются в архиве:/This parameter controls how paths are saved in the archive:
rem ep1 означает, что базовая часть будет исключена из путей в архиве (F:\Games\Subnautica\world\)/ep1 means that the basic part will be excluded from the archive paths (F:\Games\Subnautica\world\)
rem Пример: файл F:\Games\Subnautica\world\savegame\file1.dat в архиве будет сохранён как savegame\file1.dat/Example: File F:\Games\Subnautica\world\savegame\file1.dat in the archive will be saved as savegame\file1.dat
rem Альтернативы: -ep (полное исключение всех путей) или без параметра (полные пути сохраняются)/Alternatives: -ep (complete exclusion of all paths) or without parameter (full paths are preserved)

rem -m5 - уровень сжатия (Method)/Compression Level (Method)
rem Задаёт степень сжатия файлов:/Sets the compression ratio of files:
rem m0 - без сжатия (просто упаковка)/m0 - Without compression (just packaging)
rem m1 - самый быстрый (минимальное сжатие)/m1 - Fastest (minimal compression)
rem m2 - быстрый/m2 - Fast
rem m3 - обычный (стандартный)/m3 - Normal (Standard)
rem m4 - хороший (хорошее сжатие)/m4 - Good (good compression)
rem m5 - максимальный (лучшее сжатие, но медленнее)/m5 - Maximum (better compression, but slower)
rem m6 - максимальный (более агрессивный алгоритм)/m6 - Maximum (more aggressive algorithm)

rem -ibck - фоновый режим (In Background)/Background mode (In Background)
rem Запускает WinRAR в фоне (сворачивается в трей)/Runs WinRAR in the background (collapses into the tray)
rem Позволяет продолжать пользоваться компьютером, пока создаётся архив/Allows you to continue using your computer while the archive is being created
rem Очень полезно для автоматических бэкапов, чтобы не мешать работе/Very useful for automatic backups so as not to interfere with work
