import PyInstaller.__main__

PyInstaller.__main__.run([
    "backuper.py",
    "--onefile",
    "--windowed",
    "--clean",
    "--noconfirm",
    "--name", "BackuperGUI",
    "--icon", "Backuper.ico",
    "--add-data", "Backuper.ico;.",
    "--add-data", "BackUp everyone.bat;.",
    "--add-data", "BackUp with cycle.bat;.",
    "--add-data", "2.Wrapper for bat (\u041e\u0431\u0435\u0440\u0442\u043a\u0430 \u0434\u043b\u044f .bat).vbs;.",
])
