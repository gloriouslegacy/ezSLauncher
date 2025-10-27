"""
File Search & Launcher Application
Advanced file search with execution capabilities and context menu integration
"""

import os
import sys
import json
import subprocess
import threading
import re
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any

# Configuration file path
CONFIG_FILE = "app_config.json"

class FileItem:
    """Represents a file item in the search results"""
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.stat = os.stat(path)
        self.size = self.stat.st_size
        self.modified = datetime.fromtimestamp(self.stat.st_mtime)
        self.extension = os.path.splitext(path)[1]
        
    def get_size_str(self) -> str:
        """Convert file size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if self.size < 1024.0:
                return f"{self.size:.2f} {unit}"
            self.size /= 1024.0
        return f"{self.size:.2f} PB"
    
    def get_type(self) -> str:
        """Get file type description"""
        if os.path.isdir(self.path):
            return "Folder"
        return self.extension.upper()[1:] + " File" if self.extension else "File"


class SearchFilter:
    """Handles search filtering logic with regex support"""
    def __init__(self, name_filter: str = "", ext_filter: str = "", path_filter: str = "", use_regex: bool = False):
        self.use_regex = use_regex
        
        # Support multiple values separated by comma, semicolon, or space
        if use_regex:
            # For regex mode, compile patterns
            self.name_filters = []
            self.ext_filters = []
            self.path_filters = []
            
            for f in name_filter.replace(',', '|').replace(';', '|').split('|') if name_filter else []:
                f = f.strip()
                if f:
                    try:
                        self.name_filters.append(re.compile(f, re.IGNORECASE))
                    except re.error:
                        # If regex is invalid, treat as literal string
                        self.name_filters.append(re.compile(re.escape(f), re.IGNORECASE))
            
            for f in ext_filter.replace(',', '|').replace(';', '|').split('|') if ext_filter else []:
                f = f.strip()
                if f:
                    try:
                        # Auto-add dot if not present in pattern
                        if not f.startswith('.') and not f.startswith('\\'):
                            f = '\\.' + f
                        self.ext_filters.append(re.compile(f + '$', re.IGNORECASE))
                    except re.error:
                        self.ext_filters.append(re.compile(re.escape('.' + f) + '$', re.IGNORECASE))
            
            for f in path_filter.replace(',', '|').replace(';', '|').split('|') if path_filter else []:
                f = f.strip()
                if f:
                    try:
                        self.path_filters.append(re.compile(f, re.IGNORECASE))
                    except re.error:
                        self.path_filters.append(re.compile(re.escape(f), re.IGNORECASE))
        else:
            # Normal mode - simple string matching
            self.name_filters = [f.strip().lower() for f in name_filter.replace(',', ' ').replace(';', ' ').split() if f.strip()]
            self.ext_filters = [f.strip().lower() if f.strip().startswith('.') else '.' + f.strip().lower() 
                               for f in ext_filter.replace(',', ' ').replace(';', ' ').split() if f.strip()]
            self.path_filters = [f.strip().lower() for f in path_filter.replace(',', ' ').replace(';', ' ').split() if f.strip()]
    
    def matches(self, file_item: FileItem) -> bool:
        """Check if file matches all filters (OR logic within each filter type, AND logic between types)"""
        if self.use_regex:
            # Regex matching mode
            # Name filter (OR logic - matches if ANY pattern matches)
            if self.name_filters:
                if not any(pattern.search(file_item.name) for pattern in self.name_filters):
                    return False
            
            # Extension filter (OR logic - matches if ANY pattern matches)
            if self.ext_filters:
                if not any(pattern.search(file_item.extension) for pattern in self.ext_filters):
                    return False
            
            # Path filter (OR logic - matches if ANY pattern matches)
            if self.path_filters:
                if not any(pattern.search(file_item.path) for pattern in self.path_filters):
                    return False
        else:
            # Normal string matching mode
            # Name filter (OR logic - matches if ANY name filter matches)
            if self.name_filters:
                if not any(name_filter in file_item.name.lower() for name_filter in self.name_filters):
                    return False
            
            # Extension filter (OR logic - matches if ANY extension matches)
            if self.ext_filters:
                if not any(file_item.extension.lower() == ext_filter for ext_filter in self.ext_filters):
                    return False
            
            # Path filter (OR logic - matches if ANY path filter matches)
            if self.path_filters:
                if not any(path_filter in file_item.path.lower() for path_filter in self.path_filters):
                    return False
        
        return True


class FileSearchApp:
    """Main application class"""
    
    # Language translations
    LANGUAGES = {
        "English": {
            "title": "ezSLauncher",
            "menu_view": "View",
            "menu_language": "Language",
            "menu_dark_mode": "Dark Mode",
            "menu_help": "Help",
            "menu_about": "About",
            "menu_github": "Visit GitHub",
            "search_filters": "Search Filters",
            "name": "Name:",
            "extension": "Extension:",
            "path_contains": "Path Contains:",
            "tip": "💡 Tip: Use comma, semicolon, or space to separate multiple values (e.g., 'exe, msi' or 'pdf;docx')",
            "use_regex": "Use Regular Expression",
            "regex_tip": "💡 Regex Examples: '.*\\.exe$' (ends with .exe), '^test.*' (starts with test), 'report_\\d{4}' (report_+4 digits)",
            "search_directory": "Search Directory:",
            "browse": "Browse...",
            "include_subdirs": "Include Subdirectories",
            "search": "🔍 Search",
            "execute_selected": "▶ Execute Selected",
            "clear_results": "🗑 Clear Results",
            "select_all": "☑ Select All",
            "select_none": "☐ Select None",
            "export_results": "💾 Export Results",
            "results": "Results:",
            "search_results": "Search Results",
            "type": "Type",
            "modified_date": "Modified Date",
            "size": "Size",
            "full_path": "Full Path",
            "ready": "Ready",
            "searching": "Searching...",
            "found_files": "Found {0} file(s)",
            "results_cleared": "Results cleared",
            "dark_mode_enabled": "Dark mode enabled",
            "dark_mode_disabled": "Dark mode disabled",
            "language_changed": "Language changed to {0}",
            "opening_github": "Opening GitHub repository...",
            "about_title": "About File Search & Launcher",
            # "version": "Version 0.2.0",
            "description": "Advanced file search and execution tool\nwith multiple filter support",
            "created_by": "Created by: ",
            "copyright": "© 2025 All rights reserved",
            "close": "Close",
            "open": "Open",
            "run_as_admin": "Run as Administrator",
            "open_location": "Open File Location",
            "copy_path": "Copy Path",
            "properties": "Properties",
            "execute_confirm": "Execute {0} selected file(s)?",
            "confirm_execution": "Confirm Execution",
            "no_selection": "No Selection",
            "select_files_msg": "Please select files to execute.",
            "executing": "Executing {0}/{1}: {2}",
            "completed_executing": "Completed executing {0} file(s)",
            "executed": "Executed: {0}",
            "opened_location": "Opened file location",
            "copied_path": "Copied path to clipboard",
            "search_in_progress": "Search in Progress",
            "search_already_running": "A search is already in progress.",
            "invalid_directory": "Invalid Directory",
            "invalid_directory_msg": "Please select a valid search directory.",
            "no_results": "No Results",
            "no_results_export": "No search results to export.",
            "export_complete": "Export Complete",
            "exported_to": "Results exported to:\n{0}",
            "execution_error": "Execution Error",
            "export_error": "Export Error",
            "error": "Error",
            "file_properties": "File Properties",
            "location": "Location:",
        },
        "한국어": {
            "title": "ezSLauncher",
            "menu_view": "보기",
            "menu_language": "언어",
            "menu_dark_mode": "다크 모드",
            "menu_help": "도움말",
            "menu_about": "정보",
            "menu_github": "GitHub 방문",
            "search_filters": "검색 필터",
            "name": "이름:",
            "extension": "확장자:",
            "path_contains": "경로 포함:",
            "tip": "💡 팁: 쉼표, 세미콜론 또는 공백으로 여러 값을 구분하세요 (예: 'exe, msi' 또는 'pdf;docx')",
            "use_regex": "정규 표현식 사용",
            "regex_tip": "💡 정규식 예제: '.*\\.exe$' (exe로 끝남), '^test.*' (test로 시작), 'report_\\d{4}' (report_+숫자4자리)",
            "search_directory": "검색 디렉토리:",
            "browse": "찾아보기...",
            "include_subdirs": "하위 디렉토리 포함",
            "search": "🔍 검색",
            "execute_selected": "▶ 선택 항목 실행",
            "clear_results": "🗑 결과 지우기",
            "select_all": "☑ 모두 선택",
            "select_none": "☐ 선택 해제",
            "export_results": "💾 결과 내보내기",
            "results": "결과:",
            "search_results": "검색 결과",
            "type": "유형",
            "modified_date": "수정한 날짜",
            "size": "크기",
            "full_path": "전체 경로",
            "ready": "준비",
            "searching": "검색 중...",
            "found_files": "{0}개 파일 발견",
            "results_cleared": "결과 지워짐",
            "dark_mode_enabled": "다크 모드 활성화",
            "dark_mode_disabled": "다크 모드 비활성화",
            "language_changed": "언어가 {0}(으)로 변경되었습니다",
            "opening_github": "GitHub 저장소 열기...",
            "about_title": "파일 검색 & 실행 정보",
            # "version": "버전 0.2.0",
            "description": "다중 필터 지원을 갖춘\n고급 파일 검색 및 실행 도구",
            "created_by": "제작: ",
            "copyright": "© 2025 All rights reserved",
            "close": "닫기",
            "open": "열기",
            "run_as_admin": "관리자 권한으로 실행",
            "open_location": "파일 위치 열기",
            "copy_path": "경로 복사",
            "properties": "속성",
            "execute_confirm": "선택한 {0}개 파일을 실행하시겠습니까?",
            "confirm_execution": "실행 확인",
            "no_selection": "선택 없음",
            "select_files_msg": "실행할 파일을 선택하세요.",
            "executing": "실행 중 {0}/{1}: {2}",
            "completed_executing": "{0}개 파일 실행 완료",
            "executed": "실행됨: {0}",
            "opened_location": "파일 위치 열림",
            "copied_path": "경로가 클립보드에 복사됨",
            "search_in_progress": "검색 진행 중",
            "search_already_running": "이미 검색이 진행 중입니다.",
            "invalid_directory": "잘못된 디렉토리",
            "invalid_directory_msg": "올바른 검색 디렉토리를 선택하세요.",
            "no_results": "결과 없음",
            "no_results_export": "내보낼 검색 결과가 없습니다.",
            "export_complete": "내보내기 완료",
            "exported_to": "결과를 다음으로 내보냄:\n{0}",
            "execution_error": "실행 오류",
            "export_error": "내보내기 오류",
            "error": "오류",
            "file_properties": "파일 속성",
            "location": "위치:",
        }
    }
    
    def __init__(self, root):
        self.root = root
        
        # Load configuration first for language
        self.config = self.load_config()
        
        # Language setting
        self.current_language = self.config.get("language", "English")
        if self.current_language not in self.LANGUAGES:
            self.current_language = "English"
        
        # Set title with correct language
        self.root.title(self.t("title"))
        self.root.geometry("1000x700")
        
        # Set icon if available
        self.set_icon()
        
        # Data storage
        self.search_results: List[FileItem] = []
        self.checked_items: Dict[str, bool] = {}
        self.is_searching = False
        
        # Dark mode state
        self.dark_mode = self.config.get("dark_mode", False)
        
        # Define color themes
        self.themes = {
            "light": {
                "bg": "#ffffff",
                "fg": "#000000",
                "select_bg": "#0078d7",
                "select_fg": "#ffffff",
                "entry_bg": "#ffffff",
                "entry_fg": "#000000",
                "button_bg": "#f0f0f0",
                "frame_bg": "#f0f0f0",
                "tree_bg": "#ffffff",
                "tree_fg": "#000000",
                "status_bg": "#f0f0f0",
                "tip_fg": "gray"
            },
            "dark": {
                "bg": "#1e1e1e",
                "fg": "#e0e0e0",
                "select_bg": "#0078d7",
                "select_fg": "#ffffff",
                "entry_bg": "#2d2d2d",
                "entry_fg": "#e0e0e0",
                "button_bg": "#3d3d3d",
                "frame_bg": "#252525",
                "tree_bg": "#2d2d2d",
                "tree_fg": "#e0e0e0",
                "status_bg": "#252525",
                "tip_fg": "#808080"
            }
        }
        
        # Create UI
        self.create_ui()
        
        # Apply theme
        self.apply_theme()
        
        # Load saved settings
        self.load_settings()
        
    def set_icon(self):
        """Set application icon (PyInstaller compatible)"""
        def resource_path(relative_path):
            """Get absolute path to resource, works for dev and for PyInstaller"""
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
        
        # Try different icon paths
        icon_paths = [
            resource_path("icon/icon.ico"),
            resource_path("icon/icon.png"),
            resource_path("icon.ico"),
            resource_path("icon.png"),
            "./icon/icon.ico",
            "./icon/icon.png",
            "icon.ico",
            "icon.png"
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    # Try .ico file first (best for Windows)
                    if icon_path.endswith('.ico'):
                        self.root.iconbitmap(icon_path)
                        return
                except Exception as e:
                    pass
                
                try:
                    # Try PNG with iconphoto
                    if icon_path.endswith('.png'):
                        img = tk.PhotoImage(file=icon_path)
                        self.root.iconphoto(True, img)
                        return
                except Exception as e:
                    pass
    
    def create_menu_bar(self):
        """Create menu bar with Help menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # View menu for dark mode and language
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.t("menu_view"), menu=view_menu)
        
        # Language submenu
        language_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label=self.t("menu_language"), menu=language_menu)
        
        self.language_var = tk.StringVar(value=self.current_language)
        for lang in self.LANGUAGES.keys():
            language_menu.add_radiobutton(
                label=lang,
                variable=self.language_var,
                value=lang,
                command=lambda l=lang: self.change_language(l)
            )
        
        view_menu.add_separator()
        
        # Dark mode toggle
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        view_menu.add_checkbutton(label=self.t("menu_dark_mode"), variable=self.dark_mode_var, command=self.toggle_dark_mode)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.t("menu_help"), menu=help_menu)
        help_menu.add_command(label=self.t("menu_about"), command=self.show_about)
        help_menu.add_separator()
        help_menu.add_command(label=self.t("menu_github"), command=self.open_github)
    
    def show_about(self):
        """Show About dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title(self.t("about_title"))
        about_window.geometry("400x220")
        about_window.resizable(False, False)
        
        # Center the window
        about_window.transient(self.root)
        about_window.grab_set()
        
        about_frame = ttk.Frame(about_window, padding="20")
        about_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(about_frame, text=self.t("title"), font=('', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # # Version
        # version_label = ttk.Label(about_frame, text=self.t("version"), font=('', 10))
        # version_label.pack(pady=(0, 10))
        
        # Description
        desc_label = ttk.Label(about_frame, text=self.t("description"), 
                              justify=tk.CENTER)
        desc_label.pack(pady=(0, 20))
        
        # GitHub link
        github_frame = ttk.Frame(about_frame)
        github_frame.pack(pady=(0, 10))
        
        ttk.Label(github_frame, text=self.t("created_by")).pack(side=tk.LEFT)
        
        # Clickable link
        link_label = ttk.Label(github_frame, text="gloriouslegacy", foreground="blue", cursor="hand2")
        link_label.pack(side=tk.LEFT)
        link_label.bind("<Button-1>", lambda e: self.open_github())
        
        # Copyright
        copyright_label = ttk.Label(about_frame, text=self.t("copyright"), font=('', 8), foreground="gray")
        copyright_label.pack(pady=(10, 0))
        
        # Close button
        close_btn = ttk.Button(about_frame, text=self.t("close"), command=about_window.destroy)
        close_btn.pack(pady=(20, 0))
    
    def open_github(self):
        """Open GitHub repository in browser"""
        import webbrowser
        url = "https://github.com/gloriouslegacy/"
        try:
            webbrowser.open(url)
            self.update_status(self.t("opening_github"))
        except Exception as e:
            messagebox.showerror(self.t("error"), f"Failed to open browser:\n{str(e)}")
    
    def t(self, key):
        """Get translation for current language"""
        return self.LANGUAGES.get(self.current_language, self.LANGUAGES["English"]).get(key, key)
    
    def change_language(self, language):
        """Change application language"""
        self.current_language = language
        self.language_var.set(language)
        self.save_settings()
        
        # Update window title
        self.root.title(self.t("title"))
        
        # Refresh UI
        self.refresh_ui()
        
        self.update_status(self.t("language_changed").format(language))
    
    def refresh_ui(self):
        """Refresh UI text labels after language change"""
        # Clear all widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Recreate menu bar
        self.create_menu_bar()
        
        # Recreate entire UI
        self.create_ui()
        
        # Reapply theme
        self.apply_theme()
        
        # Reload settings into UI
        self.load_settings()
        
        # If there were search results, inform user they were cleared
        if self.search_results:
            self.search_results = []
            self.checked_items = {}
            self.update_status(self.t("results_cleared"))
    
    def toggle_dark_mode(self):
        """Toggle between light and dark mode"""
        self.dark_mode = self.dark_mode_var.get()
        self.apply_theme()
        self.save_settings()
        self.update_status("Dark mode " + ("enabled" if self.dark_mode else "disabled"))
    
    def apply_theme(self):
        """Apply current theme to all widgets"""
        theme = self.themes["dark"] if self.dark_mode else self.themes["light"]
        
        # Apply to root window
        self.root.configure(bg=theme["bg"])
        
        # Apply to all frames recursively
        self.apply_theme_recursive(self.root, theme)
    
    def apply_theme_recursive(self, widget, theme):
        """Recursively apply theme to all child widgets"""
        try:
            widget_class = widget.winfo_class()
            
            # Main window
            if widget_class == "Tk":
                widget.configure(bg=theme["bg"])
            
            # Frames and LabelFrames
            elif widget_class in ["Frame", "Labelframe"]:
                widget.configure(bg=theme["bg"])
                # For LabelFrame, also set label color
                if widget_class == "Labelframe":
                    try:
                        style = ttk.Style()
                        style.configure("TLabelframe", background=theme["bg"], foreground=theme["fg"])
                        style.configure("TLabelframe.Label", background=theme["bg"], foreground=theme["fg"])
                    except:
                        pass
            
            # Labels
            elif widget_class == "Label":
                # Check if it's a special label (like the tip or github link)
                current_fg = None
                try:
                    current_fg = widget.cget("foreground")
                except:
                    pass
                
                if current_fg == "blue":  # Keep blue links
                    widget.configure(bg=theme["bg"])
                elif current_fg in ["gray", "#808080"]:  # Tip text
                    widget.configure(bg=theme["bg"], fg=theme["tip_fg"])
                else:
                    widget.configure(bg=theme["bg"], fg=theme["fg"])
            
            # Buttons
            elif widget_class == "Button":
                try:
                    style = ttk.Style()
                    style.configure("TButton", background=theme["button_bg"], foreground=theme["fg"])
                except:
                    pass
            
            # Checkbuttons
            elif widget_class == "Checkbutton":
                try:
                    style = ttk.Style()
                    style.configure("TCheckbutton", background=theme["bg"], foreground=theme["fg"])
                except:
                    pass
            
            # Entries
            elif widget_class == "Entry":
                widget.configure(bg=theme["entry_bg"], fg=theme["entry_fg"], 
                               insertbackground=theme["fg"], disabledbackground=theme["entry_bg"],
                               disabledforeground=theme["tip_fg"])
            
            # Treeview
            elif widget_class == "Treeview":
                style = ttk.Style()
                if self.dark_mode:
                    style.theme_use('default')
                    style.configure("Treeview",
                                  background=theme["tree_bg"],
                                  foreground=theme["tree_fg"],
                                  fieldbackground=theme["tree_bg"],
                                  borderwidth=0)
                    style.map('Treeview',
                            background=[('selected', theme["select_bg"])],
                            foreground=[('selected', theme["select_fg"])])
                    style.configure("Treeview.Heading",
                                  background=theme["button_bg"],
                                  foreground=theme["fg"],
                                  borderwidth=1)
                    style.map("Treeview.Heading",
                            background=[('active', theme["select_bg"])])
                else:
                    style.theme_use('default')
                    style.configure("Treeview",
                                  background=theme["tree_bg"],
                                  foreground=theme["tree_fg"],
                                  fieldbackground=theme["tree_bg"])
                    style.configure("Treeview.Heading",
                                  background=theme["button_bg"],
                                  foreground=theme["fg"])
        except Exception as e:
            pass  # Skip widgets that don't support these options
        
        # Recursively apply to children
        for child in widget.winfo_children():
            self.apply_theme_recursive(child, theme)
    
    def create_ui(self):
        """Create user interface"""
        # Create menu bar
        self.create_menu_bar()
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Search filter section
        self.create_filter_section(main_frame)
        
        # Control buttons
        self.create_control_section(main_frame)
        
        # Results section
        self.create_results_section(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
    
    def create_filter_section(self, parent):
        """Create search filter input section"""
        filter_frame = ttk.LabelFrame(parent, text=self.t("search_filters"), padding="10")
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Configure grid weights for equal expansion
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)
        filter_frame.columnconfigure(5, weight=1)
        
        # Name filter
        ttk.Label(filter_frame, text=self.t("name")).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.name_filter = ttk.Entry(filter_frame)
        self.name_filter.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 20))
        
        # Extension filter
        ttk.Label(filter_frame, text=self.t("extension")).grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.ext_filter = ttk.Entry(filter_frame)
        self.ext_filter.grid(row=0, column=3, sticky=(tk.W, tk.E), padx=(0, 20))
        
        # Path filter
        ttk.Label(filter_frame, text=self.t("path_contains")).grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.path_filter = ttk.Entry(filter_frame)
        self.path_filter.grid(row=0, column=5, sticky=(tk.W, tk.E))
        
        # Help text for multiple filters
        help_text = ttk.Label(filter_frame, text=self.t("tip"), 
                             foreground="gray", font=('', 8))
        help_text.grid(row=2, column=0, columnspan=6, sticky=tk.W, pady=(5, 0))
        
        # Search directory
        ttk.Label(filter_frame, text=self.t("search_directory")).grid(row=1, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.search_dir = ttk.Entry(filter_frame)
        self.search_dir.grid(row=1, column=1, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0), padx=(0, 5))
        
        browse_btn = ttk.Button(filter_frame, text=self.t("browse"), command=self.browse_directory)
        browse_btn.grid(row=1, column=5, pady=(10, 0), sticky=tk.W)
        
        # Recursive search option and regex option
        options_frame = ttk.Frame(filter_frame)
        options_frame.grid(row=3, column=0, columnspan=6, sticky=tk.W, pady=(5, 0))
        
        self.recursive_var = tk.BooleanVar(value=True)
        recursive_check = ttk.Checkbutton(options_frame, text=self.t("include_subdirs"), variable=self.recursive_var)
        recursive_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # Regex option checkbox
        self.regex_var = tk.BooleanVar(value=False)
        regex_check = ttk.Checkbutton(options_frame, text=self.t("use_regex"), variable=self.regex_var, command=self.toggle_regex_tip)
        regex_check.pack(side=tk.LEFT)
        
        # Regex help text (initially hidden)
        self.regex_tip = ttk.Label(filter_frame, text=self.t("regex_tip"), 
                             foreground="gray", font=('', 8))
        # Will be shown/hidden by toggle_regex_tip
    
    def create_control_section(self, parent):
        """Create control buttons section"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Search button
        self.search_btn = ttk.Button(control_frame, text=self.t("search"), command=self.start_search, width=15)
        self.search_btn.grid(row=0, column=0, padx=(0, 10))
        
        # Execute selected button
        execute_btn = ttk.Button(control_frame, text=self.t("execute_selected"), command=self.execute_selected, width=18)
        execute_btn.grid(row=0, column=1, padx=(0, 10))
        
        # Clear results button
        clear_btn = ttk.Button(control_frame, text=self.t("clear_results"), command=self.clear_results, width=15)
        clear_btn.grid(row=0, column=2, padx=(0, 10))
        
        # Export results button
        export_btn = ttk.Button(control_frame, text=self.t("export_results"), command=self.export_results, width=15)
        export_btn.grid(row=0, column=6, padx=(20, 0))
        
        # Select all/none
        select_all_btn = ttk.Button(control_frame, text=self.t("select_all"), command=self.select_all, width=12)
        select_all_btn.grid(row=0, column=3, padx=(0, 5))
        
        select_none_btn = ttk.Button(control_frame, text=self.t("select_none"), command=self.select_none, width=12)
        select_none_btn.grid(row=0, column=4)
        
        # Results count label
        self.results_label = ttk.Label(control_frame, text=self.t("results") + " 0")
        self.results_label.grid(row=0, column=5, padx=(20, 0))
    
    def create_results_section(self, parent):
        """Create results display section with treeview"""
        results_frame = ttk.LabelFrame(parent, text=self.t("search_results"), padding="10")
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(results_frame)
        tree_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type", "modified", "size", "path"),
            show="tree headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=20
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Configure columns (width and stretch)
        self.tree.column("#0", width=250, stretch=False)
        self.tree.column("type", width=100, stretch=False)
        self.tree.column("modified", width=150, stretch=False)
        self.tree.column("size", width=100, stretch=False)
        self.tree.column("path", width=500, stretch=True, minwidth=500)  # Wider path column
        
        # Bind events
        self.tree.bind("<Double-Button-1>", self.on_double_click)
        self.tree.bind("<Button-1>", self.on_single_click)  # Add single click for checkbox
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<space>", self.toggle_check)
        
        # Add sorting functionality - bind heading clicks with translations
        self.tree.heading("#0", text=self.t("name").rstrip(':'), command=lambda: self.sort_column("#0", False))
        self.tree.heading("type", text=self.t("type"), command=lambda: self.sort_column("type", False))
        self.tree.heading("modified", text=self.t("modified_date"), command=lambda: self.sort_column("modified", False))
        self.tree.heading("size", text=self.t("size"), command=lambda: self.sort_column("size", False))
        self.tree.heading("path", text=self.t("full_path"), command=lambda: self.sort_column("path", False))
        
        # Track sort state for each column
        self.sort_reverse = {}
        
        # Create checkbutton images
        self.create_check_images()
    
    def sort_column(self, col, reverse):
        """Sort treeview by column"""
        # Get all items with their data
        items = [(self.tree.set(item, col) if col != "#0" else self.tree.item(item, "text"), item) 
                 for item in self.tree.get_children("")]
        
        # Handle special sorting for different columns
        if col == "size":
            # Sort by size (convert to bytes for proper numeric sorting)
            def size_to_bytes(size_str):
                if not size_str:
                    return 0
                parts = size_str.split()
                if len(parts) != 2:
                    return 0
                value, unit = parts
                try:
                    value = float(value)
                    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                    return value * multipliers.get(unit, 1)
                except:
                    return 0
            items = [(size_to_bytes(val), item) for val, item in items]
        elif col == "modified":
            # Sort by date (already in sortable format YYYY-MM-DD HH:MM:SS)
            pass
        else:
            # Text sorting - case insensitive
            items = [(val.lower() if isinstance(val, str) else val, item) for val, item in items]
        
        # Sort items
        items.sort(reverse=reverse)
        
        # Rearrange items in tree
        for index, (val, item) in enumerate(items):
            self.tree.move(item, "", index)
        
        # Toggle sort direction for next click
        new_reverse = not reverse
        self.tree.heading(col, command=lambda: self.sort_column(col, new_reverse))
        
        # Update column header to show sort direction
        current_text = self.tree.heading(col, "text")
        # Remove existing arrows
        base_text = current_text.replace(" ▲", "").replace(" ▼", "")
        # Add arrow
        arrow = " ▼" if reverse else " ▲"
        self.tree.heading(col, text=base_text + arrow)
    
    def create_check_images(self):
        """Create checkbox images for tree items"""
        self.check_images = {
            'checked': '☑',
            'unchecked': '☐'
        }
    
    def create_status_bar(self, parent):
        """Create status bar at bottom"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text=self.t("ready"), relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # GitHub link in status bar
        github_label = ttk.Label(status_frame, text="gloriouslegacy", foreground="blue", cursor="hand2", 
                                relief=tk.SUNKEN, padding=(5, 2))
        github_label.pack(side=tk.RIGHT, padx=(5, 0))
        github_label.bind("<Button-1>", lambda e: self.open_github())
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=200)
        self.progress.pack(side=tk.RIGHT, padx=(10, 0))
    
    def browse_directory(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory(initialdir=self.search_dir.get() or os.path.expanduser("~"))
        if directory:
            self.search_dir.delete(0, tk.END)
            self.search_dir.insert(0, directory)
    
    def toggle_regex_tip(self):
        """Show or hide regex tip based on checkbox state"""
        if self.regex_var.get():
            # Show regex tip
            self.regex_tip.grid(row=4, column=0, columnspan=6, sticky=tk.W, pady=(5, 0))
        else:
            # Hide regex tip
            self.regex_tip.grid_forget()
    
    def start_search(self):
        """Start file search in background thread"""
        if self.is_searching:
            messagebox.showwarning("Search in Progress", "A search is already in progress.")
            return
        
        search_dir = self.search_dir.get()
        if not search_dir or not os.path.exists(search_dir):
            messagebox.showerror("Invalid Directory", "Please select a valid search directory.")
            return
        
        # Disable search button
        self.search_btn.config(state=tk.DISABLED)
        self.is_searching = True
        
        # Show and start progress bar
        self.progress.pack(side=tk.RIGHT, padx=(10, 0))
        self.progress.start(10)
        self.update_status("Searching...")
        
        # Save settings
        self.save_settings()
        
        # Start search thread
        thread = threading.Thread(target=self.perform_search, daemon=True)
        thread.start()
    
    def perform_search(self):
        """Perform file search (runs in background thread)"""
        try:
            search_dir = self.search_dir.get()
            search_filter = SearchFilter(
                self.name_filter.get(),
                self.ext_filter.get(),
                self.path_filter.get(),
                self.regex_var.get()
            )
            
            results = []
            recursive = self.recursive_var.get()
            
            if recursive:
                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            file_item = FileItem(file_path)
                            if search_filter.matches(file_item):
                                results.append(file_item)
                        except (PermissionError, OSError):
                            continue
            else:
                try:
                    for item in os.listdir(search_dir):
                        file_path = os.path.join(search_dir, item)
                        if os.path.isfile(file_path):
                            try:
                                file_item = FileItem(file_path)
                                if search_filter.matches(file_item):
                                    results.append(file_item)
                            except (PermissionError, OSError):
                                continue
                except (PermissionError, OSError):
                    pass
            
            # Update UI in main thread
            self.root.after(0, self.display_results, results)
            
        except Exception as e:
            self.root.after(0, messagebox.showerror, "Search Error", f"Error during search: {str(e)}")
        finally:
            self.root.after(0, self.search_complete)
    
    def display_results(self, results: List[FileItem]):
        """Display search results in treeview"""
        # Clear existing results
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.search_results = results
        self.checked_items.clear()
        
        # Add results to tree
        for file_item in results:
            item_id = self.tree.insert(
                "",
                tk.END,
                text=f"☐ {file_item.name}",
                values=(
                    file_item.get_type(),
                    file_item.modified.strftime("%Y-%m-%d %H:%M:%S"),
                    file_item.get_size_str(),
                    file_item.path
                )
            )
            self.checked_items[item_id] = False
        
        # Update results label
        self.results_label.config(text=f"Results: {len(results)}")
        self.update_status(f"Found {len(results)} file(s)")
    
    def search_complete(self):
        """Called when search is complete"""
        self.is_searching = False
        self.search_btn.config(state=tk.NORMAL)
        self.progress.stop()
        # Hide progress bar by unpacking
        self.progress.pack_forget()
    
    def toggle_check(self, event=None):
        """Toggle checkbox for selected item"""
        selection = self.tree.selection()
        if not selection:
            return
        
        for item_id in selection:
            current_state = self.checked_items.get(item_id, False)
            new_state = not current_state
            self.checked_items[item_id] = new_state
            
            # Update display
            current_text = self.tree.item(item_id, "text")
            if new_state:
                new_text = "☑" + current_text[1:]
            else:
                new_text = "☐" + current_text[1:]
            self.tree.item(item_id, text=new_text)
    
    def select_all(self):
        """Select all items"""
        for item_id in self.tree.get_children():
            self.checked_items[item_id] = True
            current_text = self.tree.item(item_id, "text")
            self.tree.item(item_id, text="☑" + current_text[1:])
    
    def select_none(self):
        """Deselect all items"""
        for item_id in self.tree.get_children():
            self.checked_items[item_id] = False
            current_text = self.tree.item(item_id, "text")
            self.tree.item(item_id, text="☐" + current_text[1:])
    
    def on_double_click(self, event):
        """Handle double-click to execute file"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        # Execute file (don't toggle checkbox on double-click)
        file_path = self.tree.item(item_id, "values")[3]
        self.execute_file(file_path, admin=False)
    
    def on_single_click(self, event):
        """Handle single-click for checkbox toggling"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        # Check if clicked on checkbox area (first 30 pixels of tree column)
        region = self.tree.identify_region(event.x, event.y)
        if region == "tree":
            try:
                bbox = self.tree.bbox(item_id)
                if bbox:
                    x_offset = event.x - bbox[0]
                    if x_offset < 30:  # Clicked on checkbox area
                        # Select the item first
                        self.tree.selection_set(item_id)
                        # Toggle checkbox
                        current_state = self.checked_items.get(item_id, False)
                        new_state = not current_state
                        self.checked_items[item_id] = new_state
                        
                        # Update display
                        current_text = self.tree.item(item_id, "text")
                        if new_state:
                            new_text = "☑" + current_text[1:]
                        else:
                            new_text = "☐" + current_text[1:]
                        self.tree.item(item_id, text=new_text)
            except:
                pass
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        self.tree.selection_set(item_id)
        file_path = self.tree.item(item_id, "values")[3]
        
        # Create context menu
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Open", command=lambda: self.execute_file(file_path, admin=False))
        context_menu.add_command(label="Run as Administrator", command=lambda: self.execute_file(file_path, admin=True))
        context_menu.add_separator()
        context_menu.add_command(label="Open File Location", command=lambda: self.open_file_location(file_path))
        context_menu.add_command(label="Copy Path", command=lambda: self.copy_path(file_path))
        context_menu.add_separator()
        context_menu.add_command(label="Properties", command=lambda: self.show_properties(file_path))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def execute_file(self, file_path: str, admin: bool = False):
        """Execute a file"""
        try:
            if admin:
                # Run as administrator on Windows
                if sys.platform == 'win32':
                    subprocess.Popen(['runas', '/user:Administrator', file_path], shell=True)
                else:
                    subprocess.Popen(['sudo', file_path])
            else:
                # Normal execution
                if sys.platform == 'win32':
                    os.startfile(file_path)
                else:
                    subprocess.Popen(['xdg-open', file_path])
            
            self.update_status(f"Executed: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to execute file:\n{str(e)}")
    
    def open_file_location(self, file_path: str):
        """Open file location in explorer"""
        try:
            directory = os.path.dirname(file_path)
            if sys.platform == 'win32':
                # Use shell=True for Windows explorer command
                subprocess.Popen(f'explorer /select,"{file_path}"', shell=True)
            else:
                subprocess.Popen(['xdg-open', directory])
            self.update_status(f"Opened file location")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open location:\n{str(e)}")
    
    def copy_path(self, file_path: str):
        """Copy file path to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(file_path)
        self.update_status(f"Copied path to clipboard")
    
    def show_properties(self, file_path: str):
        """Show file properties dialog"""
        try:
            file_item = FileItem(file_path)
            
            props_window = tk.Toplevel(self.root)
            props_window.title("File Properties")
            props_window.geometry("500x300")
            props_window.resizable(False, False)
            
            props_frame = ttk.Frame(props_window, padding="20")
            props_frame.pack(fill=tk.BOTH, expand=True)
            
            properties = [
                ("Name:", file_item.name),
                ("Type:", file_item.get_type()),
                ("Location:", os.path.dirname(file_path)),
                ("Size:", file_item.get_size_str()),
                ("Modified:", file_item.modified.strftime("%Y-%m-%d %H:%M:%S")),
                ("Full Path:", file_path)
            ]
            
            for i, (label, value) in enumerate(properties):
                ttk.Label(props_frame, text=label, font=('', 10, 'bold')).grid(row=i, column=0, sticky=tk.W, pady=5, padx=(0, 10))
                ttk.Label(props_frame, text=value, wraplength=350).grid(row=i, column=1, sticky=tk.W, pady=5)
            
            ttk.Button(props_frame, text="Close", command=props_window.destroy).grid(row=len(properties), column=0, columnspan=2, pady=(20, 0))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show properties:\n{str(e)}")
    
    def execute_selected(self):
        """Execute all selected files sequentially in background"""
        checked_files = [
            self.tree.item(item_id, "values")[3]
            for item_id, checked in self.checked_items.items()
            if checked
        ]
        
        if not checked_files:
            messagebox.showinfo("No Selection", "Please select files to execute.")
            return
        
        # Confirm execution
        if not messagebox.askyesno("Confirm Execution", f"Execute {len(checked_files)} selected file(s)?"):
            return
        
        # Execute in background thread
        thread = threading.Thread(target=self.execute_files_sequentially, args=(checked_files,), daemon=True)
        thread.start()
    
    def execute_files_sequentially(self, file_paths: List[str]):
        """Execute files sequentially (runs in background thread)"""
        for i, file_path in enumerate(file_paths, 1):
            try:
                self.root.after(0, self.update_status, f"Executing {i}/{len(file_paths)}: {os.path.basename(file_path)}")
                
                if sys.platform == 'win32':
                    os.startfile(file_path)
                else:
                    subprocess.Popen(['xdg-open', file_path])
                
                # Small delay between executions
                import time
                time.sleep(0.5)
                
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Execution Error", f"Failed to execute {file_path}:\n{str(e)}")
        
        self.root.after(0, self.update_status, f"Completed executing {len(file_paths)} file(s)")
    
    def clear_results(self):
        """Clear search results"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.search_results.clear()
        self.checked_items.clear()
        self.results_label.config(text="Results: 0")
        self.update_status("Results cleared")
    
    def export_results(self):
        """Export search results to CSV file"""
        if not self.search_results:
            messagebox.showinfo("No Results", "No search results to export.")
            return
        
        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Export Results"
        )
        
        if not file_path:
            return
        
        try:
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(["Name", "Type", "Modified Date", "Size", "Full Path"])
                
                # Write data
                for file_item in self.search_results:
                    writer.writerow([
                        file_item.name,
                        file_item.get_type(),
                        file_item.modified.strftime("%Y-%m-%d %H:%M:%S"),
                        file_item.get_size_str(),
                        file_item.path
                    ])
            
            messagebox.showinfo("Export Complete", f"Results exported to:\n{file_path}")
            self.update_status(f"Exported {len(self.search_results)} results to CSV")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results:\n{str(e)}")
    
    def update_status(self, message: str):
        """Update status bar message"""
        self.status_label.config(text=message)
    
    def save_settings(self):
        """Save current settings to config file"""
        self.config = {
            "name_filter": self.name_filter.get(),
            "ext_filter": self.ext_filter.get(),
            "path_filter": self.path_filter.get(),
            "search_dir": self.search_dir.get(),
            "recursive": self.recursive_var.get(),
            "use_regex": self.regex_var.get(),
            "dark_mode": self.dark_mode,
            "language": self.current_language
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load config: {e}")
        return {}
    
    def load_settings(self):
        """Load saved settings into UI"""
        # Set default search directory to user profile
        default_dir = os.path.expanduser("~")
        
        if self.config:
            self.name_filter.insert(0, self.config.get("name_filter", ""))
            self.ext_filter.insert(0, self.config.get("ext_filter", ""))
            self.path_filter.insert(0, self.config.get("path_filter", ""))
            self.search_dir.insert(0, self.config.get("search_dir", default_dir))
            self.recursive_var.set(self.config.get("recursive", True))
            self.regex_var.set(self.config.get("use_regex", False))
            # Show regex tip if regex is enabled
            if self.regex_var.get():
                self.toggle_regex_tip()
        else:
            # No config file - set default userprofile path
            self.search_dir.insert(0, default_dir)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = FileSearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()