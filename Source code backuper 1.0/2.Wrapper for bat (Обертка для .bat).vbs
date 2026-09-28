' Скрипт запуска игры и бэкапов
Option Explicit

' Создание лога
Dim shell, fso, logPath
Set shell = CreateObject("WScript.Shell")
Set fso   = CreateObject("Scripting.FileSystemObject")

' Путь к логам
logPath = "H:\BackUper\BackUper v0.2.2\launch_log.txt"

Sub Log(msg)
    Dim f: Set f = fso.OpenTextFile(logPath, 8, True)
    f.WriteLine Now() & " - " & msg
    f.Close
End Sub

On Error Resume Next

' Путь к папке в которой лежит игра
shell.CurrentDirectory = "F:\Games\Subnautica"
If Err.Number <> 0 Then Log "Ошибка CurrentDirectory: " & Err.Description: WScript.Quit
Err.Clear

' Путь к игре и ее запуск
shell.Run """F:\Games\Subnautica\Nitrox.Launcher.exe""", 1, False
If Err.Number <> 0 Then Log "Ошибка запуска игры: " & Err.Description: WScript.Quit
Err.Clear
Log "Игра запущена"

' Ожидание 40 секунд
WScript.Sleep 40000 

' Путь к бат-файлу единоразового резервного копирования
shell.Run """H:\BackUper\BackUper v0.2.2\BackUp everyone.bat""", 0, False
If Err.Number <> 0 Then Log "Ошибка BackUp everyone.bat: " & Err.Description: WScript.Quit
Err.Clear
Log "BackUp everyone.bat запущен"

' Ожидание 15 секунд
WScript.Sleep 15000  

' Путь к бат-файлу цикличного резервного копирования
shell.Run """H:\BackUper\BackUper v0.2.2\BackUp with cycle.bat""", 0, False
If Err.Number <> 0 Then Log "Ошибка BackUp with cycle.bat: " & Err.Description: WScript.Quit
Err.Clear
Log "BackUp with cycle.bat запущен"

Log "Скрипт завершён"
Set shell = Nothing
Set fso   = Nothing