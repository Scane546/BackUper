import os
import re
import sys
import json
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

APP_NAME = "BackuperGUI"
VERSION = "1.0.0"
CONFIG_FILE = "config.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
CONFIG_PATH = CONFIG_DIR / CONFIG_FILE

DEFAULT_CONFIG = {
    "exe_path": "",
    "root_folder": "",
    "backup_folder": "",
    "saves_folder": "",
    "scripts_folder": "",
    "compression_level": 5,
    "check_interval": 10,
    "check_interval_unit": "сек",
    "archive_interval": 120,
    "archive_interval_unit": "сек",
    "trial_delay": 40,
    "trial_delay_unit": "сек",
    "cycle_delay": 15,
    "cycle_delay_unit": "сек",
    "base_name": "backup",
    "winrar_path": r"C:\Program Files\WinRAR\WinRAR.exe",
}

TIME_UNITS = ["сек", "мин", "час"]
TIME_MULTIPLIERS = {"сек": 1, "мин": 60, "час": 3600}


class SpinBox(ctk.CTkFrame):
    def __init__(self, master, from_=0, to=100, default=1, step=1, width=140, prefix="", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.from_ = from_
        self.to = to
        self.step = step
        self.prefix = prefix
        self.var = ctk.IntVar(value=default)

        self.minus_btn = ctk.CTkButton(self, text="-", width=30, height=30,
                                        command=self._decrement, font=("", 14, "bold"))
        self.minus_btn.pack(side="left", padx=(0, 2))

        self.entry = ctk.CTkEntry(self, width=60, height=30, justify="center",
                                   font=("", 13))
        self.entry.pack(side="left")
        self.entry.bind("<FocusOut>", self._validate_input)
        self.entry.bind("<Return>", self._validate_input)
        self._update_display()

        self.plus_btn = ctk.CTkButton(self, text="+", width=30, height=30,
                                       command=self._increment, font=("", 14, "bold"))
        self.plus_btn.pack(side="left", padx=(2, 0))

        self.var.trace_add("write", lambda *_: self._update_display())

    def _update_display(self):
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.insert(0, f"{self.prefix}{self.var.get()}")

    def _increment(self):
        val = self.var.get()
        if val + self.step <= self.to:
            self.var.set(val + self.step)

    def _decrement(self):
        val = self.var.get()
        if val - self.step >= self.from_:
            self.var.set(val - self.step)

    def _validate_input(self, event=None):
        try:
            text = self.entry.get().replace(self.prefix, "").strip()
            val = int(text)
            val = max(self.from_, min(self.to, val))
            self.var.set(val)
        except (ValueError, TypeError):
            self.var.set(self.from_)

    def get(self):
        return self.var.get()

    def set(self, value):
        self.var.set(value)


class BackuperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("680x680")
        self.minsize(680, 680)
        self.maxsize(680, 680)
        self.resizable(False, False)

        self._center_window()

        self.config_data = {}
        self.is_running = False
        self.check_timer = None
        self.archive_timer = None
        self._last_backup_time = 0

        self._load_config()
        self._build_ui()
        self._fill_fields()

        icon_path = self._tmpl(self._app_dir(), "Backuper.ico")
        if os.path.isfile(icon_path):
            if not self._set_win_icon(icon_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path).convert("RGBA")
                    self._icon_img = ImageTk.PhotoImage(img)
                    self.iconphoto(True, self._icon_img)
                except Exception:
                    try:
                        self.iconbitmap(icon_path)
                    except Exception:
                        pass

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _load_config(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.config_data = DEFAULT_CONFIG.copy()
        else:
            self.config_data = DEFAULT_CONFIG.copy()

    def _save_config(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = self._collect_config()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        scrollable = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scrollable.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        scrollable.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_paths_section(scrollable)
        self._build_params_section(scrollable)
        self._build_name_section(scrollable)
        self._build_log_section(scrollable)
        self._build_bottom_bar()

    def _section_frame(self, parent, title):
        frame = ctk.CTkFrame(parent, corner_radius=8)
        frame.grid_columnconfigure(1, weight=1)
        label = ctk.CTkLabel(frame, text=title, font=("", 14, "bold"), anchor="w")
        label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))
        return frame

    def _browse_file(self, entry, filetypes=None):
        if filetypes is None:
            filetypes = [("Executable", "*.exe"), ("All files", "*.*")]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _browse_folder(self, entry):
        path = filedialog.askdirectory()
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _make_path_row(self, parent, row, label_text, filetypes=None, description=""):
        lbl = ctk.CTkLabel(parent, text=label_text, anchor="w", width=180)
        lbl.grid(row=row, column=0, padx=(10, 5), pady=5, sticky="w")

        entry = ctk.CTkEntry(parent, placeholder_text="Выберите путь...")
        entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")

        if filetypes == "folder":
            cmd = lambda e=entry: self._browse_folder(e)
        else:
            cmd = lambda e=entry, ft=filetypes: self._browse_file(e, ft)

        btn = ctk.CTkButton(parent, text="Обзор", width=70, command=cmd)
        btn.grid(row=row, column=2, padx=(5, 10), pady=5)

        if description:
            desc = ctk.CTkLabel(parent, text=description, font=("", 10), text_color="gray", anchor="w")
            desc.grid(row=row + 1, column=0, columnspan=3, padx=15, pady=(0, 5), sticky="w")

        return entry

    def _make_spinner_row(self, parent, row, label_text, from_, to, default, step=1, unit="", prefix=""):
        lbl = ctk.CTkLabel(parent, text=label_text, anchor="w", width=180)
        lbl.grid(row=row, column=0, padx=(10, 5), pady=5, sticky="w")

        spinner = SpinBox(parent, from_=from_, to=to, default=default, step=step, prefix=prefix)
        spinner.grid(row=row, column=1, padx=5, pady=5, sticky="w")

        if unit:
            unit_lbl = ctk.CTkLabel(parent, text=unit, anchor="w")
            unit_lbl.grid(row=row, column=2, padx=(5, 10), pady=5, sticky="w")

        return spinner

    def _make_interval_row(self, parent, row, label_text, from_, to, default, default_unit="сек"):
        lbl = ctk.CTkLabel(parent, text=label_text, anchor="w", width=180)
        lbl.grid(row=row, column=0, padx=(10, 5), pady=5, sticky="w")

        spinner = SpinBox(parent, from_=from_, to=to, default=default, step=1)
        spinner.grid(row=row, column=1, padx=5, pady=5, sticky="w")

        unit_menu = ctk.CTkOptionMenu(parent, values=TIME_UNITS, width=70, height=30)
        unit_menu.set(default_unit)
        unit_menu.grid(row=row, column=2, padx=(5, 10), pady=5, sticky="w")

        return spinner, unit_menu

    def _to_seconds(self, spinner, unit_menu):
        return spinner.get() * TIME_MULTIPLIERS[unit_menu.get()]

    @staticmethod
    def _app_dir():
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _tmpl(self, program_dir, name):
        local = os.path.join(program_dir, name)
        if os.path.isfile(local):
            return local
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            bundled = os.path.join(sys._MEIPASS, name)
            if os.path.isfile(bundled):
                return bundled
        return local

    def _set_win_icon(self, icon_path):
        try:
            self.iconbitmap(icon_path)
            return True
        except Exception:
            return False

    def _build_paths_section(self, parent):
        frame = self._section_frame(parent, "Пути к файлам и папкам")
        frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        self.exe_entry = self._make_path_row(frame, 1, "EXE-файл игры:")

        proc_lbl = ctk.CTkLabel(frame, text="Имя процесса:", anchor="w", width=180)
        proc_lbl.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="w")
        self.process_entry = ctk.CTkEntry(frame, placeholder_text="Например: 7DaysToDie.exe")
        self.process_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.root_entry = self._make_path_row(frame, 3, "Корневая папка игры:", "folder")
        self.backup_entry = self._make_path_row(frame, 5, "Сохранение бэкапов:", "folder",
            description="В данной папке создастся папка _backups/, в которую будут помещаться сами бэкапы")
        self.saves_entry = self._make_path_row(frame, 7, "Папка сохранений:", "folder")
        self.scripts_entry = self._make_path_row(frame, 8, "Сохранение файлов Backuper:", "folder", description="Внутри создастся папка Backuper со сгенерированными файлами")
        self.winrar_entry = self._make_path_row(frame, 9, "Путь к WinRAR.exe:")

    def _build_params_section(self, parent):
        frame = self._section_frame(parent, "Параметры бэкапа")
        frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        self.compression_spinner = self._make_spinner_row(
            frame, 1, "Уровень сжатия:", 0, 5, 5, 1, "m0-m5", prefix="m")
        self.check_interval_spinner, self.check_unit_menu = self._make_interval_row(
            frame, 2, "Интервал проверки процесса:", 1, 3600, 10)
        self.archive_interval_spinner, self.archive_unit_menu = self._make_interval_row(
            frame, 3, "Интервал архивации:", 1, 86400, 120)
        self.trial_delay_spinner, self.trial_delay_unit_menu = self._make_interval_row(
            frame, 4, "Задержка перед стартом пробного бэкапа:", 0, 3600, 40)
        self.cycle_delay_spinner, self.cycle_delay_unit_menu = self._make_interval_row(
            frame, 5, "Задержка до начала цикла:", 0, 3600, 15)

    def _build_name_section(self, parent):
        frame = self._section_frame(parent, "Имя и иконка")
        frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        lbl = ctk.CTkLabel(frame, text="Имя профиля:", anchor="w", width=180)
        lbl.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        self.name_entry = ctk.CTkEntry(frame, placeholder_text="Латиница, цифры, _ (для бэкапа и ярлыка)")
        self.name_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        desc = ctk.CTkLabel(frame, text="Это имя используется в названии бэкапа (переменная NAME) и в имени ярлыка", font=("", 10), text_color="gray", anchor="w")
        desc.grid(row=2, column=0, columnspan=3, padx=15, pady=(0, 5), sticky="w")

        self.use_exe_icon_var = ctk.BooleanVar(value=True)
        self.use_exe_icon_check = ctk.CTkCheckBox(
            frame, text="Поставить иконку программы на ярлык",
            variable=self.use_exe_icon_var
        )
        self.use_exe_icon_check.grid(row=3, column=0, columnspan=3, padx=15, pady=(0, 5), sticky="w")

    def _build_log_section(self, parent):
        frame = self._section_frame(parent, "Лог событий")
        frame.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 10))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        self.log_text = ctk.CTkTextbox(frame, height=120, state="disabled", wrap="word")
        self.log_text.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")

    def _build_bottom_bar(self):
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)

        self.save_btn = ctk.CTkButton(
            bottom, text="Сохранить отредактированные файлы в выбранную папку",
            height=36, command=self._on_save
        )
        self.save_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.shortcut_btn = ctk.CTkButton(
            bottom, text="Создать ярлык", width=130, height=36,
            command=self._on_create_shortcut
        )
        self.shortcut_btn.grid(row=0, column=1, padx=(5, 0), sticky="e")

    def _set_fields_state(self, state):
        widgets = [
            self.exe_entry, self.process_entry, self.root_entry,
            self.backup_entry, self.saves_entry, self.scripts_entry,
            self.winrar_entry, self.name_entry, self.use_exe_icon_check
        ]
        for w in widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass

        spinners = [
            self.compression_spinner,
            self.check_interval_spinner, self.archive_interval_spinner,
            self.trial_delay_spinner, self.cycle_delay_spinner
        ]
        for s in spinners:
            try:
                s.entry.configure(state=state)
            except Exception:
                pass

        unit_menus = [self.check_unit_menu, self.archive_unit_menu,
                      self.trial_delay_unit_menu, self.cycle_delay_unit_menu]
        for menu in unit_menus:
            try:
                menu.configure(state=state)
            except Exception:
                pass

    def _validate(self):
        exe = self.exe_entry.get().strip()
        process = self.process_entry.get().strip()
        root = self.root_entry.get().strip()
        backup = self.backup_entry.get().strip()
        saves = self.saves_entry.get().strip()
        scripts = self.scripts_entry.get().strip()
        winrar = self.winrar_entry.get().strip()
        base_name = self.name_entry.get().strip()

        if not exe:
            return "EXE-файл игры не указан"
        if not os.path.isfile(exe):
            return f"EXE-файл не найден: {exe}"

        if not process:
            return "Имя процесса не указано"

        if not root:
            return "Корневая папка игры не указана"
        if not os.path.isdir(root):
            return f"Корневая папка игры не найдена: {root}"

        if not backup:
            return "Папка сохранения бэкапов не указана"
        if not os.path.isdir(backup):
            return f"Папка сохранения бэкапов не найдена: {backup}"

        if not saves:
            return "Папка сохранений не указана"
        if not os.path.isdir(saves):
            return f"Папка сохранений не найдена: {saves}"

        if not scripts:
            return "Папка со скриптами не указана"
        if not os.path.isdir(scripts):
            return f"Папка со скриптами не найдена: {scripts}"

        if not winrar:
            return "Путь к WinRAR не указан"
        if not os.path.isfile(winrar):
            return f"WinRAR не найден: {winrar}"

        if not base_name:
            return "Имя ярлыка не указано"
        if not re.match(r'^[a-zA-Z0-9_]+$', base_name):
            return "Имя ярлыка: только латиница, цифры и _ (без пробелов)"

        if self.check_interval_spinner.get() <= 0:
            return "Интервал проверки процесса должен быть > 0"
        if self.archive_interval_spinner.get() <= 0:
            return "Интервал архивации должен быть > 0"
        if self.trial_delay_spinner.get() < 0:
            return "Задержка перед стартом пробного бэкапа не может быть отрицательной"
        if self.cycle_delay_spinner.get() < 0:
            return "Задержка до начала цикла не может быть отрицательной"

        return None

    def _collect_config(self):
        return {
            "exe_path": self.exe_entry.get().strip(),
            "game_process": self.process_entry.get().strip(),
            "root_folder": self.root_entry.get().strip(),
            "backup_folder": self.backup_entry.get().strip(),
            "saves_folder": self.saves_entry.get().strip(),
            "scripts_folder": self.scripts_entry.get().strip(),
            "winrar_path": self.winrar_entry.get().strip(),
            "compression_level": self.compression_spinner.get(),
            "check_interval": self.check_interval_spinner.get(),
            "check_interval_unit": self.check_unit_menu.get(),
            "archive_interval": self.archive_interval_spinner.get(),
            "archive_interval_unit": self.archive_unit_menu.get(),
            "trial_delay": self.trial_delay_spinner.get(),
            "trial_delay_unit": self.trial_delay_unit_menu.get(),
            "cycle_delay": self.cycle_delay_spinner.get(),
            "cycle_delay_unit": self.cycle_delay_unit_menu.get(),
            "base_name": self.name_entry.get().strip(),
            "use_exe_icon": self.use_exe_icon_var.get(),
        }

    def _fill_fields(self):
        c = self.config_data
        self.exe_entry.insert(0, c.get("exe_path", ""))
        self.process_entry.insert(0, c.get("game_process", ""))
        self.root_entry.insert(0, c.get("root_folder", ""))
        self.backup_entry.insert(0, c.get("backup_folder", ""))
        self.saves_entry.insert(0, c.get("saves_folder", ""))
        self.scripts_entry.insert(0, c.get("scripts_folder", ""))
        self.winrar_entry.insert(0, c.get("winrar_path", DEFAULT_CONFIG["winrar_path"]))
        self.name_entry.insert(0, c.get("base_name", ""))

        self.compression_spinner.set(c.get("compression_level", 5))
        self.check_interval_spinner.set(c.get("check_interval", 10))
        self.check_unit_menu.set(c.get("check_interval_unit", "сек"))
        self.archive_interval_spinner.set(c.get("archive_interval", 120))
        self.archive_unit_menu.set(c.get("archive_interval_unit", "сек"))
        self.trial_delay_spinner.set(c.get("trial_delay", 40))
        self.trial_delay_unit_menu.set(c.get("trial_delay_unit", "сек"))
        self.cycle_delay_spinner.set(c.get("cycle_delay", 15))
        self.cycle_delay_unit_menu.set(c.get("cycle_delay_unit", "сек"))
        self.use_exe_icon_var.set(c.get("use_exe_icon", True))

    def _on_save(self):
        error = self._validate()
        if error:
            messagebox.showerror("Ошибка", error)
            self._log(f"Ошибка: {error}")
            return

        self.config_data = self._collect_config()
        self._save_config()

        check_sec = self._to_seconds(self.check_interval_spinner, self.check_unit_menu)
        archive_sec = self._to_seconds(self.archive_interval_spinner, self.archive_unit_menu)
        trial_sec = self._to_seconds(self.trial_delay_spinner, self.trial_delay_unit_menu)
        cycle_sec = self._to_seconds(self.cycle_delay_spinner, self.cycle_delay_unit_menu)

        scripts_base = self.config_data["scripts_folder"].replace("/", "\\")
        scripts_dir = os.path.join(scripts_base, "Backuper")
        os.makedirs(scripts_dir, exist_ok=True)
        exe_path = self.config_data["exe_path"].replace("/", "\\")
        exe_dir = os.path.dirname(exe_path)
        game_process = self.config_data["game_process"]
        saves_folder = self.config_data["saves_folder"].replace("/", "\\")
        winrar_path = self.config_data["winrar_path"].replace("/", "\\")
        compression = self.config_data["compression_level"]
        base_name = self.config_data["base_name"]
        backup_folder = self.config_data["backup_folder"].replace("/", "\\")

        program_dir = self._app_dir()
        everyone_template = self._tmpl(program_dir, "BackUp everyone.bat")
        cycle_template = self._tmpl(program_dir, "BackUp with cycle.bat")
        vbs_template = self._tmpl(program_dir, "2.Wrapper for bat (Обертка для .bat).vbs")

        try:
            if os.path.isfile(everyone_template):
                with open(everyone_template, "r", encoding="utf-8") as f:
                    everyone_content = f.read()
                _ru_fix = {
                    'rem ???? ????????? ?????/Where to save backup': 'rem Куда сохранять бэкап/Where to save backup',
                    'rem ??? ???? ??? ??????????/Name of the game or application': 'rem Краткое имя игры или приложения/The short name of the game or application',
                    'rem ??? ?????????/What to save': 'rem Что сохранять/What to save',
                    'rem ???? ? ??? ???? (? ??? ????? ? ????????)/Path to WinRAR (I put it in the package)': 'rem Путь к винрару (я его кинул в комплект)/Path to WinRAR (I put it in the package)',
                    'rem ??????? ????? ??? ??????? ???? ? ???/Create a backup folder if it doesn\'t exist': 'rem Создать папку бэкапа, если она не существует/Create a backup folder if it doesn\'t exist',
                    'rem ??????? ??? ?????? ? ????? ? ???????? (?????-????_???;??????;???????) / Create archive name with date and time (month-day_hour;minute;second)': 'rem Создать имя архива с датой и временем (месяц-день_часы;минуты;секунды) / Create archive name with date and time (month-day_hour;minute;second)',
                    'rem ??????? ????? ? ???? ? ??????? (?? m5 ?? m0, ??? m0 ????? ?? ???????? ? m5 ?????? ??????????? ????????)/Create an archive in the background with compression (from m5 to m0, where m0 is almost uncompressed and m5 is compressed as much as possible)': 'rem Создать архив в фоне со сжатием (от m5 до m0, где m0 почти не сжимается, а m5 сжимает максимально) / Create an archive in the background with compression (from m5 to m0, where m0 is almost uncompressed and m5 is compressed as much as possible)',
                    'rem a - ?????????? ? ????? (Add)/Add to Archive (Add)': 'rem a - добавить в архив (Add)/Add to Archive (Add)',
                    'rem ??? ???????? ??????? ??? ???????? ?????? ??????. ??? ????????? WinRAR, ??? ????? ???????? ????? ? ?????./This is the main command for creating a new archive. It tells WinRAR to add files to the archive.': 'rem Это главная команда для создания нового архива. Она указывает WinRAR добавлять файлы в архив./This is the main command for creating a new archive. It tells WinRAR to add files to the archive.',
                    'rem -r - ??????????? ????? (Recursive)/Recursive traversal': 'rem -r - рекурсивный обход (Recursive)/Recursive traversal',
                    'rem ???????????? ??? ???????? ? ????? ?????? ????????? ?????/Processes all subfolders and files inside the specified folder': 'rem Обрабатывает все вложенные папки и файлы внутри указанной папки/Processes all subfolders and files inside the specified folder',
                    'rem ??? ????? ????????? WinRAR ??????? ?? ?????? ????? ?? ????? %SOURCE_FOLDER%, ?? ?? ?? ????????? ?????/Without this parameter, WinRAR would have added only files from the %SOURCE_FOLDER% root, but not from subfolders': 'rem Без этого параметра WinRAR добавил бы только файлы из корня %SOURCE_FOLDER%, но не из вложенных папок/Without this parameter, WinRAR would have added only files from the %SOURCE_FOLDER% root, but not from subfolders',
                    'rem -ep1 - ?????????? ???????? ???? (Exclude Path)/Exclude the base path (Exclude Path)': 'rem -ep1 - исключить базовый путь (Exclude Path)/Exclude the base path (Exclude Path)',
                    'rem ???? ???????? ????????? ???, ??? ???? ??????????? ? ??????:/This parameter controls how paths are saved in the archive:': 'rem Этот параметр управляет тем, как пути сохраняются в архиве:/This parameter controls how paths are saved in the archive:',
                    'rem ep1 ????????, ??? ?? ???????? ????? ????? ????????? ??????? ????? (F:\\Games\\Subnautica\\world\\)/ep1 means that the basic part will be excluded from the archive paths (F:\\Games\\Subnautica\\world\\)': 'rem ep1 означает, что базовая часть будет исключена из путей в архиве (F:\\Games\\Subnautica\\world\\)/ep1 means that the basic part will be excluded from the archive paths (F:\\Games\\Subnautica\\world\\)',
                    'rem ??????: ???? F:\\Games\\Subnautica\\world\\savegame\\file1.dat ? ?????? ????? ???????? ??? savegame\\file1.dat/Example: File F:\\Games\\Subnautica\\world\\savegame\\file1.dat in the archive will be saved as savegame\\file1.dat': 'rem Пример: файл F:\\Games\\Subnautica\\world\\savegame\\file1.dat в архиве будет сохранён как savegame\\file1.dat/Example: File F:\\Games\\Subnautica\\world\\savegame\\file1.dat in the archive will be saved as savegame\\file1.dat',
                    'rem ????????????: -ep (?????? ?????????? ???? ?????) ??? ??? ????????? (??????????? ?????? ????)/Alternatives: -ep (complete exclusion of all paths) or without parameter (full paths are preserved)': 'rem Альтернативы: -ep (полное исключение всех путей) или без параметра (полные пути сохраняются)/Alternatives: -ep (complete exclusion of all paths) or without parameter (full paths are preserved)',
                    'rem -m5 - ??????? ?????? (Method)/Compression Level (Method)': 'rem -m5 - уровень сжатия (Method)/Compression Level (Method)',
                    'rem ?????? ??????? ?????? ??????:/Sets the compression ratio of files:': 'rem Задаёт степень сжатия файлов:/Sets the compression ratio of files:',
                    'rem m0 - ??? ?????? (?????? ????????)/m0 - Without compression (just packaging)': 'rem m0 - без сжатия (просто упаковка)/m0 - Without compression (just packaging)',
                    'rem m1 - ????? ??????? (??????????? ??????)/m1 - Fastest (minimal compression)': 'rem m1 - самый быстрый (минимальное сжатие)/m1 - Fastest (minimal compression)',
                    'rem m2 - ???????/m2 - Fast': 'rem m2 - быстрый/m2 - Fast',
                    'rem m3 - ??????? (???????????)/m3 - Normal (Standard)': 'rem m3 - обычный (стандартный)/m3 - Normal (Standard)',
                    'rem m4 - ??????? (??????? ??????)/m4 - Good (good compression)': 'rem m4 - хороший (хорошее сжатие)/m4 - Good (good compression)',
                    'rem m5 - ???????????? (?????? ??????, ?? ?????????)/m5 - Maximum (better compression, but slower)': 'rem m5 - максимальный (лучшее сжатие, но медленнее)/m5 - Maximum (better compression, but slower)',
                    'rem m6 - ???????????? (????? ??????????? ????????)/m6 - Maximum (more aggressive algorithm)': 'rem m6 - максимальный (более агрессивный алгоритм)/m6 - Maximum (more aggressive algorithm)',
                    'rem -ibck - ??????? ????? (In Background)/Background mode (In Background)': 'rem -ibck - фоновый режим (In Background)/Background mode (In Background)',
                    'rem ????????? WinRAR ? ??????? ?????? (??????????? ? ????)/Runs WinRAR in the background (collapses into the tray)': 'rem Запускает WinRAR в фоне (сворачивается в трей)/Runs WinRAR in the background (collapses into the tray)',
                    'rem ????????? ?????????? ???????????? ?????????, ???? ????????? ?????/Allows you to continue using your computer while the archive is being created': 'rem Позволяет продолжать пользоваться компьютером, пока создаётся архив/Allows you to continue using your computer while the archive is being created',
                    'rem ????? ??????? ??? ?????????????? ???????, ????? ?? ?????? ??????/Very useful for automatic backups so as not to interfere with work': 'rem Очень полезно для автоматических бэкапов, чтобы не мешать работе/Very useful for automatic backups so as not to interfere with work',
                }
                for _bad, _good in _ru_fix.items():
                    if _bad in everyone_content:
                        everyone_content = everyone_content.replace(_bad, _good)
                everyone_content = everyone_content.replace('\tset "BACKUP_PATH=C:\\Users\\Scane\\AppData\\Roaming\\Nitrox\\saves"', f'\tset "BACKUP_PATH={backup_folder}\\_backups"')
                everyone_content = everyone_content.replace('\tset "NAME=Subna"', f'\tset "NAME={base_name}"')
                everyone_content = everyone_content.replace('\tset "SOURCE_FOLDER=C:\\Users\\Scane\\AppData\\Roaming\\7DaysToDie\\Saves\\BackUp\\BackUps"', f'\tset "SOURCE_FOLDER={saves_folder}"')
                everyone_content = everyone_content.replace('\tset "WINRAR=C:\\Program Files\\WinRAR\\WinRAR.exe"', f'\tset "WINRAR={winrar_path}"')
                everyone_content = everyone_content.replace('\tstart "" "%WINRAR%" a -r -ep1 -m5 -ibck -idc -y', f'\tstart "" "%WINRAR%" a -r -ep1 -m{compression} -ibck -idc -y')
                with open(os.path.join(scripts_dir, "BackUp everyone.bat"), "w", encoding="utf-8") as f:
                    f.write(everyone_content)
                self._log("Создан: BackUp everyone.bat")
            else:
                self._log(f"Шаблон не найден: {everyone_template}")

            if os.path.isfile(cycle_template):
                with open(cycle_template, "r", encoding="utf-8") as f:
                    cycle_content = f.read()
                cycle_content = cycle_content.replace('\tset "BACKUP_PATH=C:\\Users\\Scane\\AppData\\Roaming\\Nitrox\\saves"', f'\tset "BACKUP_PATH={backup_folder}\\_backups"')
                cycle_content = cycle_content.replace('\tset "NAME=Subna"', f'\tset "NAME={base_name}"')
                cycle_content = cycle_content.replace('\tset "SOURCE_FOLDER=C:\\Users\\Scane\\AppData\\Roaming\\7DaysToDie\\Saves\\BackUp\\BackUps"', f'\tset "SOURCE_FOLDER={saves_folder}"')
                cycle_content = cycle_content.replace('\tset "WINRAR=C:\\Program Files\\WinRAR\\WinRAR.exe"', f'\tset "WINRAR={winrar_path}"')
                cycle_content = cycle_content.replace('\tset "GAME_PROCESS=Nitrox.Launcher.exe"', f'\tset "GAME_PROCESS={game_process}"')
                cycle_content = cycle_content.replace('\tset "CHECK_INTERVAL=10"', f'\tset "CHECK_INTERVAL={check_sec}"')
                cycle_content = cycle_content.replace('\tset "BACKUP_INTERVAL=10"', f'\tset "BACKUP_INTERVAL={archive_sec}"')
                cycle_content = cycle_content.replace('start "" "%WINRAR%" a -r -ep1 -m5 -ibck -idc -y', f'start "" "%WINRAR%" a -r -ep1 -m{compression} -ibck -idc -y')
                with open(os.path.join(scripts_dir, "BackUp with cycle.bat"), "w", encoding="utf-8") as f:
                    f.write(cycle_content)
                self._log("Создан: BackUp with cycle.bat")
            else:
                self._log(f"Шаблон не найден: {cycle_template}")

            if os.path.isfile(vbs_template):
                with open(vbs_template, "r", encoding="utf-8") as f:
                    vbs_content = f.read()
                vbs_content = vbs_content.replace('logPath = "H:\\BackUper\\BackUper v0.2.2\\launch_log.txt"', f'logPath = "{scripts_dir}\\launch_log.txt"')
                vbs_content = vbs_content.replace('shell.CurrentDirectory = "F:\\Games\\Subnautica"', f'shell.CurrentDirectory = "{exe_dir}"')
                vbs_content = vbs_content.replace('shell.Run """F:\\Games\\Subnautica\\Nitrox.Launcher.exe""", 1, False', f'shell.Run """{exe_path}""", 1, False')
                vbs_content = vbs_content.replace('shell.Run """H:\\BackUper\\BackUper v0.2.2\\BackUp everyone.bat""", 0, False', f'shell.Run """{scripts_dir}\\BackUp everyone.bat""", 0, False')
                vbs_content = vbs_content.replace('shell.Run """H:\\BackUper\\BackUper v0.2.2\\BackUp with cycle.bat""", 0, False', f'shell.Run """{scripts_dir}\\BackUp with cycle.bat""", 0, False')
                vbs_content = vbs_content.replace('WScript.Sleep 40000 ', f'WScript.Sleep {trial_sec * 1000} ')
                vbs_content = vbs_content.replace('WScript.Sleep 15000  ', f'WScript.Sleep {cycle_sec * 1000}  ')
                with open(os.path.join(scripts_dir, "2.Wrapper for bat (Обертка для .bat).vbs"), "w", encoding="utf-8") as f:
                    f.write(vbs_content)
                self._log("Создан: 2.Wrapper for bat (Обертка для .bat).vbs")
            else:
                self._log(f"Шаблон не найден: {vbs_template}")

            self._log(f"Все файлы сохранены в: {scripts_dir}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файлы:\n{e}")
            self._log(f"Ошибка сохранения: {e}")

    def _on_create_shortcut(self):
        error = self._validate()
        if error:
            messagebox.showerror("Ошибка", error)
            return

        self.config_data = self._collect_config()
        self._save_config()

        self._create_shortcut()

    def _create_shortcut(self):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        scripts_base = self.scripts_entry.get().strip().replace("/", "\\")
        scripts_dir = os.path.join(scripts_base, "Backuper")
        vbs_path = os.path.join(scripts_dir, "2.Wrapper for bat (Обертка для .bat).vbs")
        shortcut_name = self.name_entry.get().strip() or "Backuper"
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")

        if not os.path.isfile(vbs_path):
            messagebox.showerror("Ошибка", f"Обертка VBS не найдена:\n{vbs_path}\n\nСначала нажмите 'Сохранить отредактированные файлы'")
            return

        icon_path = ""
        if self.use_exe_icon_var.get():
            if getattr(sys, "frozen", False):
                icon_path = sys.executable
            else:
                icon_path = self._tmpl(self._app_dir(), "Backuper.ico")

        ps_cmd = f'''
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut('{shortcut_path}')
        $sc.TargetPath = '{vbs_path}'
        $sc.WorkingDirectory = '{scripts_dir}'
        $sc.Description = '{APP_NAME}'
        '''
        if icon_path and os.path.isfile(icon_path):
            ps_cmd += f"$sc.IconLocation = '{icon_path},0'\n"
        ps_cmd += "$sc.Save()"
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._log(f"Ярлык создан: {shortcut_path}")
            self._log(f"Цель: 2.Wrapper for bat (Обертка для .bat).vbs")
        except Exception as e:
            self._log(f"Ошибка создания ярлыка: {e}")

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def on_closing(self):
        if self.is_running:
            if messagebox.askyesno("Выход", "Бэкап выполняется. Остановить и выйти?"):
                self._stop_backup()
                self.destroy()
        else:
            self.destroy()


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "BackuperGUI.Unique.ID"
        )
    except Exception:
        pass
    app = BackuperApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
