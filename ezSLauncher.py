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
import configparser
import shutil
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any

def get_config_dir():
    """Get application config directory in %APPDATA%"""
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA')
        if appdata:
            config_dir = os.path.join(appdata, 'ezSLauncher')
        else:
            config_dir = os.path.expanduser('~/.ezSLauncher')
    else:
        config_dir = os.path.expanduser('~/.ezSLauncher')
    
    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

CONFIG_DIR = get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "app_config.json")
LANG_DIR = "languages"

# Update configuration
GITHUB_REPO = "gloriouslegacy/ezSLauncher"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "0.0.0"  # Will be updated by version_info.txt during build

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

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
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    def get_type(self) -> str:
        """Get file type description"""
        if os.path.isdir(self.path):
            return "Folder"
        return self.extension.upper()[1:] + " File" if self.extension else "File"


class SearchFilter:
    """Handles search filtering logic with regex support"""
    def __init__(self, name_filter: str = "", ext_filter: str = "", path_filter: str = "", use_regex: bool = False):
        self.use_regex = use_regex
        
        if use_regex:
            self.name_filters = []
            self.ext_filters = []
            self.path_filters = []
            
            for f in name_filter.replace(',', '|').replace(';', '|').split('|') if name_filter else []:
                f = f.strip()
                if f:
                    try:
                        self.name_filters.append(re.compile(f, re.IGNORECASE))
                    except re.error:
                        self.name_filters.append(re.compile(re.escape(f), re.IGNORECASE))
            
            for f in ext_filter.replace(',', '|').replace(';', '|').split('|') if ext_filter else []:
                f = f.strip()
                if f:
                    try:
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
            self.name_filters = [f.strip().lower() for f in name_filter.replace(',', ' ').replace(';', ' ').split() if f.strip()]
            self.ext_filters = [f.strip().lower() if f.strip().startswith('.') else '.' + f.strip().lower() 
                               for f in ext_filter.replace(',', ' ').replace(';', ' ').split() if f.strip()]
            self.path_filters = [f.strip().lower() for f in path_filter.replace(',', ' ').replace(';', ' ').split() if f.strip()]
    
    def matches(self, file_item: FileItem) -> bool:
        """Check if file matches all filters"""
        if self.use_regex:
            if self.name_filters:
                if not any(pattern.search(file_item.name) for pattern in self.name_filters):
                    return False
            
            if self.ext_filters:
                if not any(pattern.search(file_item.extension) for pattern in self.ext_filters):
                    return False
            
            if self.path_filters:
                if not any(pattern.search(file_item.path) for pattern in self.path_filters):
                    return False
        else:
            if self.name_filters:
                if not any(name_filter in file_item.name.lower() for name_filter in self.name_filters):
                    return False
            
            if self.ext_filters:
                if not any(file_item.extension.lower() == ext_filter for ext_filter in self.ext_filters):
                    return False
            
            if self.path_filters:
                if not any(path_filter in file_item.path.lower() for path_filter in self.path_filters):
                    return False
        
        return True


class FileSearchApp:
    """Main application class"""
    
    # Default English translations
    DEFAULT_TRANSLATIONS = {
        "title": "ezSLauncher",
        "menu_view": "View",
        "menu_language": "Language",
        "menu_dark_mode": "Dark Mode",
        "menu_help": "Help",
        "menu_about": "About",
        "menu_github": "Visit GitHub",
        "menu_check_update": "Check for Updates",
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
        "stop": "⏹ Stop",
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
        "description": "Advanced file search and execution tool\nwith multiple filter support",
        "created_by": "Created by: ",
        "copyright": "© 2025 All rights reserved",
        "close": "Close",
        "open": "Open",
        "run_as_admin": "Run as Administrator",
        "open_location": "Open File Location",
        "copy_path": "Copy Path",
        "properties": "Properties",
        "open_with": "Open With",
        "delete": "Delete",
        "rename": "Rename",
        "create_shortcut": "Create Shortcut",
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
        "confirm_delete": "Are you sure you want to delete?",
        "delete_failed": "Delete failed",
        "delete_success": "Deleted: {0}",
        "rename_title": "Rename",
        "new_name": "New name:",
        "rename_failed": "Rename failed",
        "rename_success": "Renamed: {0}",
        "shortcut_created": "Shortcut created: {0}",
        "shortcut_failed": "Shortcut creation failed",
        "open_with_not_supported": "Open With is only supported on Windows",
        "shortcut_not_supported": "Shortcut creation is only supported on Windows",
        "file_exists": "File already exists",
        "copy_to": "Copy To...",
        "move_to": "Move To...",
        "add_to_startup": "Add to Startup",
        "select_destination": "Select Destination Folder",
        "copied_to": "Copied to:",
        "moved_to": "Moved to:",
        "success": "Success",
        "overwrite_confirm": "File already exists. Overwrite?",
        "already_exists": "Already Exists",
        "replace_startup_shortcut": "Replace existing startup shortcut?",
        "added_to_startup": "Added to startup programs:",
        "files": "files",
        "copy_complete": "Copy Complete",
        "move_complete": "Move Complete", 
        "startup_complete": "Startup Registration Complete",
        "skipped": "Skipped",
        "update_available": "Update Available",
        "update_available_msg": "New version {0} is available!\nCurrent version: {1}\n\nWould you like to download and install it now?",
        "no_update": "No Update Available",
        "no_update_msg": "You are already using the latest version ({0}).",
        "checking_update": "Checking for updates...",
        "downloading_update": "Downloading update...",
        "download_progress": "Downloaded: {0}%",
        "update_error": "Update Error",
        "update_error_msg": "Failed to check for updates:\n{0}",
        "update_complete": "Update Complete",
        "update_complete_msg": "Update downloaded successfully.\nThe application will restart automatically after installation is complete.",
        "verifying_checksum": "Verifying file integrity...",
        "checksum_failed": "Checksum verification failed. Update cancelled.",
        "creating_backup": "Creating backup...",
        "backup_failed": "Backup creation failed. Update cancelled.",
        "errors": "Errors",
        "destination": "Destination",
        "open_startup_folder": "Startup Folder",
        "opened_startup_folder": "Opened startup folder",
    }
    
    def __init__(self, root):
        self.root = root
        
        # Load configuration first for language
        self.config = self.load_config()
        
        # Language setting - default English
        saved_lang = self.config.get("language", "English")
        
        # Map old saved language to code
        if saved_lang == "English" or saved_lang == "en":
            self.current_language = "English"
            self.current_language_code = "en"
        elif saved_lang == "한국어" or saved_lang == "Korean" or saved_lang == "ko":
            self.current_language = "한국어"
            self.current_language_code = "ko"
        else:
            self.current_language = "English"
            self.current_language_code = "en"
        
        self.translations = self.DEFAULT_TRANSLATIONS.copy()
        
        # Load language file if not English
        if self.current_language_code != "en":
            self.load_language_file_by_code(self.current_language_code)
        
        # Set title with correct language
        self.root.title(self.t("title"))
        self.root.geometry("1052x700")
        
        # Set icon if available
        self.set_icon()
        
        # Data storage
        self.search_results: List[FileItem] = []
        self.checked_items: Dict[str, bool] = {}
        self.is_searching = False
        self.search_cancelled = False
        self.save_timer = None  # For debouncing save_settings
        
        # Dark mode state
        self.dark_mode = self.config.get("dark_mode", False)
        
        # Define color themes
        self.themes = {
            "light": {
                "bg": "#f3f3f3",              # Windows 11 light background
                "fg": "#000000",
                "select_bg": "#0067c0",       # Windows 11 accent blue
                "select_fg": "#ffffff",
                "entry_bg": "#ffffff",
                "entry_fg": "#000000",
                "button_bg": "#fbfbfb",       # Lighter button
                "frame_bg": "#f3f3f3",
                "tree_bg": "#ffffff",
                "tree_fg": "#000000",
                "status_bg": "#f9f9f9",
                "tip_fg": "#605e5c",          # Subtle gray
                "labelframe_bg": "#f3f3f3",
                "labelframe_fg": "#323130",
                "border": "#e1dfdd"           # Border color
            },
            "dark": {
                "bg": "#202020",              # Windows 11 dark main bg
                "fg": "#ffffff",              # Pure white text
                "select_bg": "#0067c0",       # Windows 11 accent blue
                "select_fg": "#ffffff",
                "entry_bg": "#2b2b2b",        # Input field bg
                "entry_fg": "#ffffff",
                "button_bg": "#2b2b2b",       # Button bg
                "frame_bg": "#202020",
                "tree_bg": "#1e1e1e",         # Slightly darker tree
                "tree_fg": "#ffffff",
                "status_bg": "#1a1a1a",       # Darker status bar
                "tip_fg": "#9d9d9d",          # Gray hints
                "labelframe_bg": "#202020",
                "labelframe_fg": "#ffffff",
                "border": "#3d3d3d"           # Subtle border
            }
        }
        
        # Create UI
        self.create_ui()
        
        # Load saved settings
        self.load_settings()
        
        # Apply initial theme
        self.apply_theme()
        
        # Check for updates on startup (after 3 seconds delay)
        self.root.after(3000, self.check_for_updates_silent)
    
    def load_language_file(self, lang_name: str):
        """Load translations from INI file (legacy method)"""
        # Convert display name to code
        lang_code = lang_name.lower()[:2]
        return self.load_language_file_by_code(lang_code)

    def load_language_file_by_code(self, lang_code: str):
        """Load translations from INI file by language code"""
        lang_file = f"lang_{lang_code}.ini"
        
        # Try multiple paths
        paths_to_try = [
            # 1. PyInstaller bundled resource (for frozen exe)
            resource_path(os.path.join("language", lang_file)),
            # 2. Next to script (for development)
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "language", lang_file),
            # 3. Current directory (for development)
            os.path.join(os.getcwd(), "language", lang_file),
        ]
        
        for lang_path in paths_to_try:
            if os.path.exists(lang_path):
                try:
                    config = configparser.ConfigParser(interpolation=None)
                    config.read(lang_path, encoding='utf-8')
                    
                    if 'UI' in config:
                        for key in config['UI']:
                            self.translations[key] = config['UI'][key]
                        return True
                    else:
                        continue
                except Exception as e:
                    print(f"Error reading {lang_path}: {e}")
                    continue
        
        return False
    
    def t(self, key: str) -> str:
        """Get translation for key"""
        return self.translations.get(key, key)
    
    def set_icon(self):
        """Set application icon if available"""
        try:
            # Try to load icon from icon folder
            icon_path = resource_path(os.path.join("icon", "icon.ico"))
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                self.icon_path = icon_path
            else:
                # Fallback to root directory
                icon_path = resource_path("icon.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
                    self.icon_path = icon_path
                else:
                    self.icon_path = None
        except Exception as e:
            print(f"Failed to load icon: {e}")
            self.icon_path = None
    
    def set_window_icon(self, window):
        """Set icon for a specific window"""
        if self.icon_path:
            try:
                window.iconbitmap(self.icon_path)
            except Exception as e:
                print(f"Failed to set window icon: {e}")
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="FILE", menu=file_menu)
        
        # Language submenu
        lang_menu = tk.Menu(file_menu, tearoff=0)
        
        # Language display name to code mapping
        self.language_map = {
            "English": "en",
            "한국어": "ko",
            "Korean": "ko"
        }
        
        # Available languages (display name -> code)
        available_langs = [("English", "en")]
        
        # Check for Korean language file
        lang_ko_path = resource_path(os.path.join("language", "lang_ko.ini"))
        if os.path.exists(lang_ko_path):
            available_langs.append(("한국어", "ko"))
        
        for lang_display, lang_code in available_langs:
            lang_menu.add_command(
                label=lang_display, 
                command=lambda ld=lang_display, lc=lang_code: self.change_language(lc, ld)
            )
        
        file_menu.add_cascade(label=self.t("menu_language"), menu=lang_menu)
        
        # Create BooleanVar for dark mode and keep reference
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        file_menu.add_checkbutton(
            label=self.t("menu_dark_mode"), 
            command=self.toggle_dark_mode,
            variable=self.dark_mode_var
        )
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="HELP", menu=help_menu)
        help_menu.add_command(label=self.t("menu_check_update"), command=self.check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label=self.t("menu_github"), command=self.open_github)
        help_menu.add_separator()
        help_menu.add_command(label=self.t("menu_about"), command=self.show_about)
    
    def toggle_dark_mode(self):
        """Toggle between light and dark mode"""
        self.dark_mode = not self.dark_mode
        
        # Update the menu checkbutton variable
        if hasattr(self, 'dark_mode_var'):
            self.dark_mode_var.set(self.dark_mode)
        
        self.apply_theme()
        self.update_status(self.t("dark_mode_enabled") if self.dark_mode else self.t("dark_mode_disabled"))
        self.save_settings()
    
    def apply_theme(self):
        """Apply current theme to all widgets"""
        theme = self.themes["dark" if self.dark_mode else "light"]
        
        # Configure ttk styles globally
        style = ttk.Style()
        
        # Set global ttk theme
        style.theme_use('default')
        
        # Configure all ttk widget styles
        style.configure(".", 
                       background=theme["bg"],
                       foreground=theme["fg"],
                       fieldbackground=theme["entry_bg"],
                       troughcolor=theme["bg"],
                       bordercolor=theme["bg"],
                       darkcolor=theme["bg"],
                       lightcolor=theme["bg"],
                       selectbackground=theme["select_bg"],
                       selectforeground=theme["select_fg"])
        
        # TFrame
        style.configure("TFrame", background=theme["bg"])
        
        # TLabel
        style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
        
        # TButton - Windows 11 style
        style.configure("TButton", 
                       background=theme["button_bg"], 
                       foreground=theme["fg"],
                       borderwidth=1,
                       relief="flat",
                       padding=(10, 5))
        style.map("TButton",
                 background=[('active', theme["select_bg"]), ('pressed', theme["select_bg"])],
                 foreground=[('active', theme["select_fg"]), ('pressed', theme["select_fg"])],
                 relief=[('pressed', 'flat')])
        
        # TEntry - Windows 11 style
        style.configure("TEntry",
                       fieldbackground=theme["entry_bg"],
                       foreground=theme["entry_fg"],
                       insertcolor=theme["fg"],
                       borderwidth=1,
                       relief="solid")
        style.map("TEntry",
                 bordercolor=[('focus', theme["select_bg"])])
        
        # TCheckbutton
        style.configure("TCheckbutton", background=theme["bg"], foreground=theme["fg"])
        
        # TLabelframe - Windows 11 style
        style.configure("TLabelframe", 
                       background=theme["labelframe_bg"],
                       foreground=theme["labelframe_fg"],
                       borderwidth=1,
                       relief="solid")
        style.configure("TLabelframe.Label",
                       background=theme["labelframe_bg"],
                       foreground=theme["labelframe_fg"],
                       font=('Segoe UI', 9, 'bold'))
        
        # Increase Treeview row height by 50%
        style.configure("Treeview", rowheight=30)
        
        # Apply to root window
        self.root.configure(bg=theme["bg"])
        
        # Apply to all widgets recursively
        self.apply_theme_recursive(self.root, theme)
        
        # Update treeview styling (zebra striping and hover colors)
        if hasattr(self, 'tree'):
            self.setup_treeview_styling()
            # Refresh all items to apply new colors
            for item in self.tree.get_children():
                self.update_item_tags(item, hover=False)
        
        # Update checkbox images for new theme
        if hasattr(self, 'check_images'):
            self.create_check_images()
            # Update all checkbox icons in tree
            if hasattr(self, 'tree') and hasattr(self, 'checked_items'):
                for item_id in self.tree.get_children():
                    current_text = self.tree.item(item_id, "text")
                    is_checked = self.checked_items.get(item_id, False)
                    icon = self.check_images['checked'] if is_checked else self.check_images['unchecked']
                    new_text = icon + current_text[1:]
                    self.tree.item(item_id, text=new_text)
    
    def apply_theme_recursive(self, widget, theme):
        """Recursively apply theme to all child widgets"""
        try:
            widget_class = widget.winfo_class()
            
            # Main window
            if widget_class == "Tk":
                widget.configure(bg=theme["bg"])
            
            # Frames and LabelFrames
            elif widget_class in ["Frame", "TFrame"]:
                if widget_class == "Frame":
                    try:
                        widget.configure(bg=theme["bg"])
                    except:
                        pass
                else:
                    # TFrame - use ttk style
                    style = ttk.Style()
                    style.configure("TFrame", background=theme["bg"])
            
            # LabelFrame styling
            elif widget_class == "TLabelframe":
                style = ttk.Style()
                style.configure("TLabelframe", background=theme["labelframe_bg"], 
                              foreground=theme["labelframe_fg"], borderwidth=2)
                style.configure("TLabelframe.Label", background=theme["labelframe_bg"], 
                              foreground=theme["labelframe_fg"])
            
            # Labels
            elif widget_class in ["Label", "TLabel"]:
                current_fg = None
                try:
                    current_fg = widget.cget("foreground")
                except:
                    pass
                
                if current_fg == "blue":
                    try:
                        widget.configure(bg=theme["bg"])
                    except:
                        pass
                elif current_fg in ["gray", "#808080"]:
                    try:
                        widget.configure(bg=theme["bg"], fg=theme["tip_fg"])
                    except:
                        pass
                else:
                    try:
                        widget.configure(bg=theme["bg"], fg=theme["fg"])
                    except:
                        pass
            
            # Buttons
            elif widget_class in ["Button", "TButton"]:
                style = ttk.Style()
                style.configure("TButton", background=theme["button_bg"], 
                              foreground=theme["fg"], borderwidth=1)
                style.map("TButton",
                         background=[('active', theme["select_bg"])],
                         foreground=[('active', theme["select_fg"])])
            
            # Checkbuttons
            elif widget_class in ["Checkbutton", "TCheckbutton"]:
                style = ttk.Style()
                style.configure("TCheckbutton", background=theme["bg"], foreground=theme["fg"])
            
            # Entries
            elif widget_class in ["Entry", "TEntry"]:
                try:
                    if widget_class == "Entry":
                        # tk.Entry widget
                        widget.configure(
                            bg=theme["entry_bg"], 
                            fg=theme["entry_fg"], 
                            insertbackground=theme["fg"],
                            disabledbackground=theme["entry_bg"],
                            disabledforeground=theme["tip_fg"],
                            selectbackground=theme["select_bg"],
                            selectforeground=theme["select_fg"]
                        )
                    else:
                        # ttk.Entry widget
                        style = ttk.Style()
                        style.configure("TEntry",
                                      fieldbackground=theme["entry_bg"],
                                      foreground=theme["entry_fg"],
                                      insertcolor=theme["fg"])
                except:
                    pass
            
            # Treeview
            elif widget_class == "Treeview":
                style = ttk.Style()
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
            
            # Scrollbar - Windows 11 style (same for both vertical and horizontal)
            elif widget_class in ["Scrollbar", "TScrollbar"]:
                style = ttk.Style()
                if self.dark_mode:
                    # Dark theme scrollbar
                    style.configure("TScrollbar",
                                  background="#3d3d3d",      # Scrollbar thumb
                                  troughcolor="#1a1a1a",     # Track background
                                  borderwidth=0,
                                  arrowcolor="#ffffff")
                    style.map("TScrollbar",
                            background=[('active', '#4d4d4d'), ('pressed', '#5d5d5d')])
                else:
                    # Light theme scrollbar
                    style.configure("TScrollbar",
                                  background="#c2c3c2",      # Scrollbar thumb
                                  troughcolor="#f3f3f3",     # Track background
                                  borderwidth=0,
                                  arrowcolor="#605e5c")
                    style.map("TScrollbar",
                            background=[('active', '#a6a6a6'), ('pressed', '#8d8d8d')])
            
        except Exception as e:
            pass
        
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
        
        # Create sections
        self.create_filter_section(main_frame)
        self.create_control_section(main_frame)
        self.create_results_section(main_frame)
        self.create_status_bar(main_frame)
        
        # Bind keyboard shortcuts
        self.setup_keyboard_shortcuts()
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        # F5 - Search
        self.root.bind('<F5>', lambda e: self.start_search())
        
        # Ctrl+A - Select All
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Control-A>', lambda e: self.select_all())
        
        # Ctrl+D - Select None
        self.root.bind('<Control-d>', lambda e: self.select_none())
        self.root.bind('<Control-D>', lambda e: self.select_none())
        
        # Delete - Delete selected file
        self.tree.bind('<Delete>', self.on_delete_key)
        
        # F2 - Rename selected file
        self.tree.bind('<F2>', self.on_rename_key)
        
        # Enter - Execute selected files
        self.tree.bind('<Return>', lambda e: self.execute_selected_files())
        
        # Ctrl+E - Export results
        self.root.bind('<Control-e>', lambda e: self.export_results())
        self.root.bind('<Control-E>', lambda e: self.export_results())
        
        # Escape - Stop search
        self.root.bind('<Escape>', lambda e: self.stop_search() if self.is_searching else None)
    
    def on_delete_key(self, event):
        """Handle Delete key press"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            file_path = self.tree.item(item)['values'][-1]
            self.delete_file(file_path)
    
    def on_rename_key(self, event):
        """Handle F2 key press"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            file_path = self.tree.item(item)['values'][-1]
            self.rename_file(file_path)
    
    def toggle_regex_tip(self):
        """Toggle regex tip visibility"""
        if self.regex_var.get():
            self.regex_tip.grid(row=5, column=0, columnspan=6, sticky=tk.W, pady=(2, 0))
        else:
            self.regex_tip.grid_remove()
        
        # Save settings when regex option changes
        self.save_settings()
    
    def create_filter_section(self, parent):
        """Create search filter section"""
        filter_frame = ttk.LabelFrame(parent, text=self.t("search_filters"), padding="10")
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        filter_frame.columnconfigure(1, weight=1)
        
        # Name filter
        ttk.Label(filter_frame, text=self.t("name")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.name_filter = ttk.Entry(filter_frame, width=40)
        self.name_filter.grid(row=0, column=1, columnspan=5, sticky=(tk.W, tk.E), pady=(0, 5), padx=(0, 5))
        
        # Extension filter
        ttk.Label(filter_frame, text=self.t("extension")).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.ext_filter = ttk.Entry(filter_frame, width=20)
        self.ext_filter.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5), padx=(0, 10))
        
        # Path filter
        ttk.Label(filter_frame, text=self.t("path_contains")).grid(row=1, column=2, sticky=tk.W, pady=(0, 5), padx=(10, 5))
        self.path_filter = ttk.Entry(filter_frame, width=30)
        self.path_filter.grid(row=1, column=3, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5), padx=(0, 5))
        
        # Tip label
        tip_label = ttk.Label(filter_frame, text=self.t("tip"), 
                             foreground="gray", font=('', 8))
        tip_label.grid(row=2, column=0, columnspan=6, sticky=tk.W, pady=(0, 5))
        
        # Search directory
        ttk.Label(filter_frame, text=self.t("search_directory")).grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        self.search_dir = ttk.Entry(filter_frame, width=60)
        self.search_dir.grid(row=3, column=1, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0), padx=(0, 5))
        
        # Bind auto-save on filter changes (with debounce)
        self.name_filter.bind('<KeyRelease>', lambda e: self.schedule_save_settings())
        self.ext_filter.bind('<KeyRelease>', lambda e: self.schedule_save_settings())
        self.path_filter.bind('<KeyRelease>', lambda e: self.schedule_save_settings())
        self.search_dir.bind('<KeyRelease>', lambda e: self.schedule_save_settings())
        
        self.browse_btn = ttk.Button(filter_frame, text=self.t("browse"), command=self.browse_directory)
        self.browse_btn.grid(row=3, column=5, pady=(10, 0), sticky=tk.W)
        
        # Options
        options_frame = ttk.Frame(filter_frame)
        options_frame.grid(row=4, column=0, columnspan=6, sticky=tk.W, pady=(5, 0))
        
        self.recursive_var = tk.BooleanVar(value=True)
        recursive_check = ttk.Checkbutton(options_frame, text=self.t("include_subdirs"), variable=self.recursive_var, command=self.save_settings)
        recursive_check.pack(side=tk.LEFT, padx=(0, 20))
        
        self.regex_var = tk.BooleanVar(value=False)
        regex_check = ttk.Checkbutton(options_frame, text=self.t("use_regex"), variable=self.regex_var, command=self.toggle_regex_tip)
        regex_check.pack(side=tk.LEFT)
        
        # Regex tip (initially hidden)
        self.regex_tip = ttk.Label(filter_frame, text=self.t("regex_tip"), 
                             foreground="gray", font=('', 8))
        # Don't grid it initially - will be shown by toggle_regex_tip if needed
    
    def create_control_section(self, parent):
        """Create control buttons section"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Search button
        self.search_btn = ttk.Button(control_frame, text=self.t("search"), command=self.start_search, width=15)
        self.search_btn.grid(row=0, column=0, padx=(0, 2))
        
        # Stop button
        self.stop_btn = ttk.Button(control_frame, text=self.t("stop"), command=self.stop_search, width=15)
        self.stop_btn.grid(row=0, column=1, padx=(0, 2))
        self.stop_btn.grid_remove()
        
        # Execute selected button
        self.execute_btn = ttk.Button(control_frame, text=self.t("execute_selected"), command=self.execute_selected, width=18)
        self.execute_btn.grid(row=0, column=2, padx=(0, 2))
        
        # Clear results button
        self.clear_btn = ttk.Button(control_frame, text=self.t("clear_results"), command=self.clear_results, width=15)
        self.clear_btn.grid(row=0, column=3, padx=(0, 2))
        
        # Select all/none
        self.select_all_btn = ttk.Button(control_frame, text=self.t("select_all"), command=self.select_all, width=12)
        self.select_all_btn.grid(row=0, column=4, padx=(0, 2))
        
        self.select_none_btn = ttk.Button(control_frame, text=self.t("select_none"), command=self.select_none, width=12)
        self.select_none_btn.grid(row=0, column=5, padx=(0, 10))
        
        # Export results button
        self.export_btn = ttk.Button(control_frame, text=self.t("export_results"), command=self.export_results, width=15)
        self.export_btn.grid(row=0, column=6, padx=(0, 2))
        
        # Startup folder button (Windows only)
        if sys.platform == 'win32':
            self.startup_btn = ttk.Button(control_frame, text="🚀 " + self.t("open_startup_folder"), 
                                         command=self.open_startup_folder, width=18)
            self.startup_btn.grid(row=0, column=7, padx=(0, 10))
        
        # Results count label - give it more space and sticky west
        self.results_label = ttk.Label(control_frame, text=self.t("results") + " 0", width=15)
        self.results_label.grid(row=0, column=8, padx=(0, 0), sticky=tk.W)
        
        # Store buttons for enabling/disabling during search
        self.control_buttons = [
            self.execute_btn,
            self.clear_btn,
            self.export_btn,
            self.select_all_btn,
            self.select_none_btn
        ]
        
        # Add startup button if it exists (Windows only)
        if sys.platform == 'win32' and hasattr(self, 'startup_btn'):
            self.control_buttons.append(self.startup_btn)
    
    def create_results_section(self, parent):
        """Create results display section with treeview"""
        results_frame = ttk.LabelFrame(parent, text=self.t("search_results"), padding="10")
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Store reference for theme updates
        self.results_frame = results_frame
        
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
        
        # Configure columns
        self.tree.column("#0", width=250, stretch=False)
        self.tree.column("type", width=100, stretch=False)
        self.tree.column("modified", width=150, stretch=False)
        self.tree.column("size", width=100, stretch=False)
        self.tree.column("path", width=500, stretch=True, minwidth=500)
        
        # Configure zebra striping (alternating row colors)
        self.setup_treeview_styling()
        
        # Bind events
        self.tree.bind("<Double-Button-1>", self.on_double_click)
        self.tree.bind("<Button-1>", self.on_single_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<space>", self.toggle_check)
        
        # Bind hover events
        self.tree.bind("<Motion>", self.on_tree_hover)
        self.tree.bind("<Leave>", self.on_tree_leave)
        self.last_hover_item = None
        
        # Add sorting
        self.tree.heading("#0", text=self.t("name").rstrip(':'), command=lambda: self.sort_column("#0", False))
        self.tree.heading("type", text=self.t("type"), command=lambda: self.sort_column("type", False))
        self.tree.heading("modified", text=self.t("modified_date"), command=lambda: self.sort_column("modified", False))
        self.tree.heading("size", text=self.t("size"), command=lambda: self.sort_column("size", False))
        self.tree.heading("path", text=self.t("full_path"), command=lambda: self.sort_column("path", False))
        
        self.sort_reverse = {}
        
        # Create checkbox images (toggle style)
        self.create_check_images()
    
    def setup_treeview_styling(self):
        """Setup zebra striping and hover effects for treeview"""
        # Define row colors based on theme
        if self.dark_mode:
            # Windows 11 Dark mode colors
            self.tree.tag_configure('oddrow', background='#1e1e1e')      # Darker
            self.tree.tag_configure('evenrow', background='#252525')     # Slightly lighter
            self.tree.tag_configure('hover', background='#2d2d2d')       # Subtle hover
            self.tree.tag_configure('checked', background='#1a3a52', foreground='#ffffff')     # Dark blue
            self.tree.tag_configure('checked_hover', background='#24537a', foreground='#ffffff')  # Lighter blue
        else:
            # Windows 11 Light mode colors
            self.tree.tag_configure('oddrow', background='#ffffff')
            self.tree.tag_configure('evenrow', background='#fafafa')
            self.tree.tag_configure('hover', background='#f3f3f3')
            self.tree.tag_configure('checked', background='#e6f2ff', foreground='#0067c0')
            self.tree.tag_configure('checked_hover', background='#cce5ff', foreground='#005a9e')
    
    def on_tree_hover(self, event):
        """Handle mouse hover over tree items"""
        item = self.tree.identify_row(event.y)
        
        if item != self.last_hover_item:
            # Remove hover from previous item
            if self.last_hover_item:
                self.update_item_tags(self.last_hover_item, hover=False)
            
            # Add hover to current item
            if item:
                self.update_item_tags(item, hover=True)
            
            self.last_hover_item = item
    
    def on_tree_leave(self, event):
        """Handle mouse leaving tree widget"""
        if self.last_hover_item:
            self.update_item_tags(self.last_hover_item, hover=False)
            self.last_hover_item = None
    
    def update_item_tags(self, item, hover=False):
        """Update tags for an item based on its state"""
        if not item:
            return
        
        # Get item index for zebra striping
        all_items = self.tree.get_children()
        try:
            index = all_items.index(item)
        except ValueError:
            index = 0
        
        is_even = index % 2 == 0
        is_checked = self.checked_items.get(item, False)
        
        # Determine appropriate tag
        if is_checked and hover:
            tags = ('checked_hover',)
        elif is_checked:
            tags = ('checked',)
        elif hover:
            tags = ('hover',)
        elif is_even:
            tags = ('evenrow',)
        else:
            tags = ('oddrow',)
        
        self.tree.item(item, tags=tags)
    
    def sort_column(self, col, reverse):
        """Sort treeview by column"""
        items = [(self.tree.set(item, col) if col != "#0" else self.tree.item(item, "text"), item) 
                 for item in self.tree.get_children("")]
        
        if col == "size":
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
            pass
        else:
            items = [(val.lower() if isinstance(val, str) else val, item) for val, item in items]
        
        items.sort(reverse=reverse)
        
        # Move items and reapply zebra striping
        for index, (val, item) in enumerate(items):
            self.tree.move(item, "", index)
            # Reapply zebra striping after sort
            self.update_item_tags(item, hover=False)
        
        new_reverse = not reverse
        self.tree.heading(col, command=lambda: self.sort_column(col, new_reverse))
        
        current_text = self.tree.heading(col, "text")
        base_text = current_text.replace(" ▲", "").replace(" ▼", "")
        arrow = " ▼" if reverse else " ▲"
        self.tree.heading(col, text=base_text + arrow)
    
    def create_check_images(self):
        """Create toggle-style checkbox images"""
        # Toggle switch style icons (more modern)
        if self.dark_mode:
            self.check_images = {
                'checked': '🟦',    # Blue square for checked
                'unchecked': '⬜'   # White square for unchecked
            }
        else:
            self.check_images = {
                'checked': '🟦',    # Blue square for checked
                'unchecked': '⬜'   # White square for unchecked
            }
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text=self.t("ready"), relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=200)
    
    def browse_directory(self):
        """Open directory browser"""
        directory = filedialog.askdirectory(initialdir=self.search_dir.get() or os.path.expanduser("~"))
        if directory:
            self.search_dir.delete(0, tk.END)
            self.search_dir.insert(0, directory)
            self.save_settings()
    
    def disable_controls(self):
        """Disable all controls during search"""
        for button in self.control_buttons:
            button.config(state='disabled')
        
        # Disable filter inputs
        self.name_filter.config(state='disabled')
        self.ext_filter.config(state='disabled')
        self.path_filter.config(state='disabled')
        self.search_dir.config(state='disabled')
        self.browse_btn.config(state='disabled')
    
    def enable_controls(self):
        """Enable all controls after search"""
        for button in self.control_buttons:
            button.config(state='normal')
        
        # Enable filter inputs
        self.name_filter.config(state='normal')
        self.ext_filter.config(state='normal')
        self.path_filter.config(state='normal')
        self.search_dir.config(state='normal')
        self.browse_btn.config(state='normal')
    
    def start_search(self):
        """Start file search in background thread"""
        if self.is_searching:
            messagebox.showinfo(self.t("search_in_progress"), self.t("search_already_running"))
            return
        
        search_dir = self.search_dir.get()
        if not search_dir or not os.path.isdir(search_dir):
            messagebox.showerror(self.t("invalid_directory"), self.t("invalid_directory_msg"))
            return
        
        # Clear previous results
        self.clear_results()
        
        # Disable controls during search
        self.disable_controls()
        
        # Show stop button, hide search button
        self.search_btn.grid_remove()
        self.stop_btn.grid()
        
        # Reset cancel flag
        self.search_cancelled = False
        self.is_searching = True
        
        # Start search in background
        search_filter = SearchFilter(
            self.name_filter.get(),
            self.ext_filter.get(),
            self.path_filter.get(),
            self.regex_var.get()
        )
        
        thread = threading.Thread(target=self.search_files, args=(search_dir, search_filter), daemon=True)
        thread.start()
    
    def stop_search(self):
        """Stop ongoing search"""
        self.search_cancelled = True
        self.update_status("Search cancelled")
    
    def search_files(self, directory: str, search_filter: SearchFilter):
        """Search files in directory"""
        try:
            self.root.after(0, self.update_status, self.t("searching"))
            
            file_count = 0
            batch = []
            batch_size = 50  # Add results in batches to reduce UI updates
            
            for root, dirs, files in os.walk(directory):
                if self.search_cancelled:
                    break
                
                for file in files:
                    if self.search_cancelled:
                        break
                    
                    try:
                        file_path = os.path.join(root, file)
                        file_item = FileItem(file_path)
                        
                        if search_filter.matches(file_item):
                            self.search_results.append(file_item)
                            batch.append(file_item)
                            file_count += 1
                            
                            # Add results in batches for better performance
                            if len(batch) >= batch_size:
                                # Schedule batch update
                                items_to_add = batch.copy()
                                self.root.after(0, self.add_results_batch, items_to_add)
                                batch.clear()
                                
                                # Update count
                                self.root.after(0, self.results_label.config, {"text": self.t("results") + f" {file_count}"})
                    except Exception as e:
                        pass
                
                if not self.recursive_var.get():
                    break
            
            # Add remaining items
            if batch:
                self.root.after(0, self.add_results_batch, batch)
            
            count = len(self.search_results)
            self.root.after(0, self.results_label.config, {"text": self.t("results") + f" {count}"})
            self.root.after(0, self.update_status, self.t("found_files").format(count))
            
        except Exception as e:
            self.root.after(0, messagebox.showerror, self.t("error"), str(e))
        finally:
            self.is_searching = False
            self.root.after(0, self.stop_btn.grid_remove)
            self.root.after(0, self.search_btn.grid)
            self.root.after(0, self.enable_controls)
    
    def add_results_batch(self, items):
        """Add multiple results to tree at once"""
        for file_item in items:
            self.add_result_to_tree(file_item)
    
    def add_result_to_tree(self, file_item: FileItem):
        """Add search result to tree with zebra striping"""
        checkbox = self.check_images['unchecked']
        
        # Get current number of items for zebra striping
        current_count = len(self.tree.get_children())
        is_even = current_count % 2 == 0
        row_tag = 'evenrow' if is_even else 'oddrow'
        
        item_id = self.tree.insert("", "end", 
                                   text=f"{checkbox} {file_item.name}",
                                   values=(
                                       file_item.get_type(),
                                       file_item.modified.strftime("%Y-%m-%d %H:%M:%S"),
                                       file_item.get_size_str(),
                                       file_item.path
                                   ),
                                   tags=(row_tag,))
        self.checked_items[item_id] = False
    
    def on_double_click(self, event):
        """Handle double click to execute file"""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            file_path = self.tree.item(item_id, "values")[3]
            self.execute_file(file_path, admin=False)
    
    def on_single_click(self, event):
        """Handle single click for checkbox"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "tree":
            item_id = self.tree.identify_row(event.y)
            if item_id:
                x_offset = event.x - self.tree.bbox(item_id)[0]
                # Increase clickable area for emoji checkboxes (emojis are wider)
                if x_offset < 50:
                    self.toggle_check_item(item_id)
    
    def toggle_check(self, event):
        """Toggle checkbox with space key"""
        selection = self.tree.selection()
        if selection:
            self.toggle_check_item(selection[0])
    
    def toggle_check_item(self, item_id):
        """Toggle checkbox state with visual feedback"""
        current_state = self.checked_items.get(item_id, False)
        new_state = not current_state
        self.checked_items[item_id] = new_state
        
        # Update checkbox icon - properly handle emoji characters
        current_text = self.tree.item(item_id, "text")
        
        # Remove old checkbox emoji (search for both types)
        for emoji in ['🟦', '⬜', '☑', '☐']:
            if current_text.startswith(emoji):
                current_text = current_text[len(emoji):].lstrip()
                break
        
        # Add new checkbox emoji
        if new_state:
            new_text = self.check_images['checked'] + ' ' + current_text
        else:
            new_text = self.check_images['unchecked'] + ' ' + current_text
        
        self.tree.item(item_id, text=new_text)
        
        # Update item tags for visual feedback
        self.update_item_tags(item_id, hover=False)
    
    def select_all(self):
        """Select all checkboxes with batch processing to prevent freezing"""
        items = self.tree.get_children()
        total = len(items)
        
        if total == 0:
            return
        
        # Disable UI updates temporarily
        self.tree.configure(takefocus=0)
        
        # Process in batches
        batch_size = 100
        for i in range(0, total, batch_size):
            batch = items[i:i+batch_size]
            for item_id in batch:
                if not self.checked_items.get(item_id, False):
                    # Update state without full UI refresh
                    self.checked_items[item_id] = True
                    current_text = self.tree.item(item_id, "text")
                    
                    # Remove old checkbox
                    for emoji in ['🟦', '⬜', '☑', '☐']:
                        if current_text.startswith(emoji):
                            current_text = current_text[len(emoji):].lstrip()
                            break
                    
                    # Add checked icon
                    new_text = self.check_images['checked'] + ' ' + current_text
                    self.tree.item(item_id, text=new_text)
                    
                    # Update visual style
                    all_items = self.tree.get_children()
                    index = all_items.index(item_id)
                    self.tree.item(item_id, tags=('checked',))
            
            # Allow UI to update periodically
            if i % (batch_size * 5) == 0:
                self.root.update_idletasks()
        
        # Re-enable UI
        self.tree.configure(takefocus=1)
        self.update_status(f"Selected {total} items")
    
    def select_none(self):
        """Deselect all checkboxes with batch processing"""
        items = self.tree.get_children()
        total = len(items)
        
        if total == 0:
            return
        
        # Disable UI updates temporarily
        self.tree.configure(takefocus=0)
        
        # Process in batches
        batch_size = 100
        for i in range(0, total, batch_size):
            batch = items[i:i+batch_size]
            for item_id in batch:
                if self.checked_items.get(item_id, False):
                    # Update state
                    self.checked_items[item_id] = False
                    current_text = self.tree.item(item_id, "text")
                    
                    # Remove old checkbox
                    for emoji in ['🟦', '⬜', '☑', '☐']:
                        if current_text.startswith(emoji):
                            current_text = current_text[len(emoji):].lstrip()
                            break
                    
                    # Add unchecked icon
                    new_text = self.check_images['unchecked'] + ' ' + current_text
                    self.tree.item(item_id, text=new_text)
                    
                    # Update visual style
                    self.update_item_tags(item_id, hover=False)
            
            # Allow UI to update periodically
            if i % (batch_size * 5) == 0:
                self.root.update_idletasks()
        
        # Re-enable UI
        self.tree.configure(takefocus=1)
        self.update_status(f"Deselected {total} items")
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        self.tree.selection_set(item_id)
        file_path = self.tree.item(item_id, "values")[3]
        
        # Get checked files
        checked_files = [
            self.tree.item(item, "values")[3]
            for item, checked in self.checked_items.items()
            if checked
        ]
        has_checked = len(checked_files) > 0
        
        # Create context menu
        context_menu = tk.Menu(self.root, tearoff=0)
        
        # Helper function to close menu then execute command
        def close_then_execute(func):
            def wrapper():
                context_menu.unpost()
                self.root.after(10, func)
            return wrapper
        
        context_menu.add_command(label=self.t("open"), command=close_then_execute(lambda: self.execute_file(file_path, admin=False)))
        context_menu.add_command(label=self.t("run_as_admin"), command=close_then_execute(lambda: self.execute_file(file_path, admin=True)))
        context_menu.add_separator()
        context_menu.add_command(label=self.t("open_with"), command=close_then_execute(lambda: self.open_with(file_path)))
        context_menu.add_command(label=self.t("open_location"), command=close_then_execute(lambda: self.open_file_location(file_path)))
        context_menu.add_separator()
        
        # Copy and Move - work with checked files if any, otherwise single file
        if has_checked:
            context_menu.add_command(
                label=f"📋 {self.t('copy_to')} ({len(checked_files)} {self.t('files')})", 
                command=close_then_execute(lambda: self.copy_files_to(checked_files))
            )
            context_menu.add_command(
                label=f"📦 {self.t('move_to')} ({len(checked_files)} {self.t('files')})", 
                command=close_then_execute(lambda: self.move_files_to(checked_files))
            )
        else:
            context_menu.add_command(label="📋 " + self.t("copy_to"), command=close_then_execute(lambda: self.copy_files_to([file_path])))
            context_menu.add_command(label="📦 " + self.t("move_to"), command=close_then_execute(lambda: self.move_files_to([file_path])))
        context_menu.add_separator()
        
        context_menu.add_command(label=self.t("rename"), command=close_then_execute(lambda: self.rename_file(file_path)))
        context_menu.add_command(label=self.t("delete"), command=close_then_execute(lambda: self.delete_file(file_path)))
        context_menu.add_command(label=self.t("create_shortcut"), command=close_then_execute(lambda: self.create_shortcut(file_path)))
        
        # Add to startup - work with checked files if any
        if sys.platform == 'win32':
            if has_checked:
                context_menu.add_command(
                    label=f"🚀 {self.t('add_to_startup')} ({len(checked_files)} {self.t('files')})", 
                    command=close_then_execute(lambda: self.add_files_to_startup(checked_files))
                )
            else:
                context_menu.add_command(label="🚀 " + self.t("add_to_startup"), command=close_then_execute(lambda: self.add_files_to_startup([file_path])))
        
        context_menu.add_separator()
        context_menu.add_command(label=self.t("copy_path"), command=close_then_execute(lambda: self.copy_path(file_path)))
        context_menu.add_command(label=self.t("properties"), command=close_then_execute(lambda: self.show_properties(file_path)))
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def execute_file(self, file_path: str, admin: bool = False):
        """Execute a file"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if admin:
                if sys.platform == 'win32':
                    import ctypes
                    
                    file_path = os.path.abspath(file_path)
                    
                    print(f"[DEBUG] Attempting to run as admin: {file_path}")
                    self.update_status(f"Running as admin: {os.path.basename(file_path)}")
                    
                    try:
                        # Use ShellExecuteW for admin execution with SW_SHOWNORMAL (1)
                        ret = ctypes.windll.shell32.ShellExecuteW(
                            None,           # hwnd
                            "runas",        # operation (verb)
                            file_path,      # file
                            None,           # parameters
                            None,           # directory
                            1               # show command (SW_SHOWNORMAL)
                        )
                        
                        print(f"[DEBUG] ShellExecuteW returned: {ret}")
                        
                        # ShellExecuteW returns > 32 for success, <= 32 for error
                        if ret <= 32:
                            error_messages = {
                                0: "Out of memory or resources",
                                2: "File not found",
                                3: "Path not found",
                                5: "Access denied (User clicked No on UAC)",
                                8: "Out of memory",
                                26: "Sharing violation",
                                27: "File association incomplete or invalid",
                                28: "DDE timeout",
                                29: "DDE transaction failed",
                                30: "DDE busy",
                                31: "No file association",
                                32: "DLL not found"
                            }
                            error_msg = error_messages.get(ret, f"Unknown error code: {ret}")
                            print(f"[DEBUG] Error: {error_msg}")
                            raise Exception(f"Failed to run as admin: {error_msg}")
                        
                        self.update_status(f"Executed as admin: {os.path.basename(file_path)}")
                        print(f"[DEBUG] Successfully executed as admin")
                    except Exception as e:
                        print(f"[DEBUG] Admin execution failed: {e}")
                        messagebox.showerror(self.t("execution_error"), str(e))
                        return
                else:
                    subprocess.Popen(['sudo', 'xdg-open', file_path])
            else:
                if sys.platform == 'win32':
                    import ctypes
                    import subprocess
                    file_path = os.path.abspath(file_path)
                    
                    # Special handling for batch files and console applications
                    if file_ext in ['.bat', '.cmd']:
                        # Run batch files in a new console window that stays open
                        # Use cmd /k to keep window open, or cmd /c to close after execution
                        subprocess.Popen(['cmd', '/k', file_path], 
                                       creationflags=subprocess.CREATE_NEW_CONSOLE)
                        print(f"Executed batch file: {file_path}")
                    elif file_ext in ['.exe', '.com']:
                        # Check if it's a console application
                        # For .exe files, use ShellExecuteW which handles both GUI and console apps
                        ret = ctypes.windll.shell32.ShellExecuteW(
                            None, "open", file_path, None, None, 1
                        )
                        
                        if ret <= 32:
                            # Fallback to subprocess for console apps
                            try:
                                subprocess.Popen([file_path], 
                                               creationflags=subprocess.CREATE_NEW_CONSOLE)
                            except Exception as e2:
                                error_messages = {
                                    0: "Out of memory or resources",
                                    2: "File not found",
                                    3: "Path not found",
                                    5: "Access denied",
                                    8: "Out of memory",
                                    26: "Sharing violation",
                                    27: "File association incomplete or invalid",
                                    28: "DDE timeout",
                                    29: "DDE transaction failed",
                                    30: "DDE busy",
                                    31: "No file association",
                                    32: "DLL not found"
                                }
                                error_msg = error_messages.get(ret, f"Unknown error code: {ret}")
                                raise Exception(f"Failed to execute: {error_msg}\nFallback also failed: {e2}")
                    else:
                        # For other file types, use ShellExecuteW
                        ret = ctypes.windll.shell32.ShellExecuteW(
                            None, "open", file_path, None, None, 1
                        )
                        
                        if ret <= 32:
                            # If ShellExecuteW fails, try os.startfile as fallback
                            try:
                                os.startfile(file_path)
                            except Exception as e2:
                                error_messages = {
                                    0: "Out of memory or resources",
                                    2: "File not found",
                                    3: "Path not found",
                                    5: "Access denied",
                                    8: "Out of memory",
                                    26: "Sharing violation",
                                    27: "File association incomplete or invalid",
                                    28: "DDE timeout",
                                    29: "DDE transaction failed",
                                    30: "DDE busy",
                                    31: "No file association",
                                    32: "DLL not found"
                                }
                                error_msg = error_messages.get(ret, f"Unknown error code: {ret}")
                                raise Exception(f"Failed to execute: {error_msg}\nFallback also failed: {e2}")
                else:
                    subprocess.Popen(['xdg-open', file_path])
            
            self.update_status(self.t("executed").format(os.path.basename(file_path)))
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(error_detail)
            messagebox.showerror(self.t("execution_error"), f"Failed to execute file:\n{str(e)}\n\nFile: {file_path}")
    
    def open_with(self, file_path: str):
        """Open file with dialog"""
        try:
            if sys.platform == 'win32':
                import ctypes
                import time
                
                # Ensure absolute path
                file_path = os.path.abspath(file_path)
                
                # Verify file exists
                if not os.path.exists(file_path):
                    messagebox.showerror(self.t("error"), f"File not found:\n{file_path}")
                    return
                
                # Method 1: Use rundll32 with process detachment (most reliable)
                try:
                    # Create a detached process that won't be terminated when parent exits
                    # DETACHED_PROCESS = 0x00000008
                    # CREATE_NEW_PROCESS_GROUP = 0x00000200
                    DETACHED_PROCESS = 0x00000008
                    CREATE_NEW_PROCESS_GROUP = 0x00000200
                    
                    # Use both flags for maximum stability
                    creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                    
                    # Start the process
                    process = subprocess.Popen(
                        ['rundll32.exe', 'shell32.dll,OpenAs_RunDLL', file_path],
                        creationflags=creation_flags,
                        shell=False,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    # Don't wait for the process - let it run independently
                    self.update_status(f"Opening 'Open With' dialog for: {os.path.basename(file_path)}")
                    return
                    
                except Exception as e1:
                    print(f"Method 1 (rundll32 detached) failed: {e1}")
                
                # Method 2: Use Windows API with proper verb
                try:
                    # Try "open" verb which sometimes shows the Open With dialog
                    # for files without association
                    ret = ctypes.windll.shell32.ShellExecuteW(
                        None,
                        None,           # Let Windows decide
                        file_path,
                        None,
                        None,
                        1
                    )
                    
                    if ret > 32:
                        self.update_status(f"Opening file: {os.path.basename(file_path)}")
                        return
                    
                    print(f"ShellExecuteW failed with code: {ret}")
                    
                except Exception as e2:
                    print(f"Method 2 (ShellExecuteW) failed: {e2}")
                
                # Method 3: Use explorer.exe to open Open With dialog
                try:
                    # This is a more modern approach
                    # Use explorer.exe with the file path
                    process = subprocess.Popen(
                        ['cmd', '/c', 'start', '', '/wait', 'rundll32.exe', 
                         'shell32.dll,OpenAs_RunDLL', file_path],
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                        shell=False,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    self.update_status(f"Opening 'Open With' dialog for: {os.path.basename(file_path)}")
                    return
                    
                except Exception as e3:
                    print(f"Method 3 (cmd start) failed: {e3}")
                
                # If all methods fail, show error
                messagebox.showerror(
                    self.t("error"), 
                    f"Failed to open 'Open With' dialog.\n\n"
                    f"File: {file_path}\n\n"
                    f"Try right-clicking the file in Windows Explorer instead."
                )
                    
            else:
                messagebox.showinfo(self.t("error"), self.t("open_with_not_supported"))
                
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messagebox.showerror(self.t("error"), f"Failed to open with:\n{str(e)}")
    
    def open_file_location(self, file_path: str):
        """Open file location in explorer"""
        try:
            if sys.platform == 'win32':
                import subprocess
                subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
            else:
                directory = os.path.dirname(file_path)
                subprocess.Popen(['xdg-open', directory])
            self.update_status(self.t("opened_location"))
        except Exception as e:
            messagebox.showerror(self.t("error"), f"Failed to open location:\n{str(e)}")
    
    def rename_file(self, file_path: str):
        """Rename file"""
        try:
            old_name = os.path.basename(file_path)
            
            # Create custom dialog
            dialog = tk.Toplevel(self.root)
            dialog.title(self.t("rename_title"))
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Set size and position
            dialog_width = 500
            dialog_height = 150
            x = (dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog_height // 2)
            dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            dialog.resizable(False, False)
            
            # Apply icon
            self.set_window_icon(dialog)
            
            # Create frame
            frame = ttk.Frame(dialog, padding="20")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Label
            label = ttk.Label(frame, text=self.t("new_name"), font=('', 11))
            label.pack(anchor=tk.W, pady=(0, 10))
            
            # Entry
            entry = ttk.Entry(frame, font=('', 11), width=50)
            entry.insert(0, old_name)
            entry.pack(fill=tk.X, pady=(0, 20))
            entry.focus_set()
            entry.select_range(0, tk.END)
            
            # Result variable
            result = {'name': None}
            
            def on_ok(event=None):
                result['name'] = entry.get()
                dialog.destroy()
            
            def on_cancel(event=None):
                dialog.destroy()
            
            # Button frame
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill=tk.X)
            
            ok_btn = ttk.Button(btn_frame, text=self.t("ok"), command=on_ok, width=12)
            ok_btn.pack(side=tk.RIGHT, padx=(5, 0))
            
            cancel_btn = ttk.Button(btn_frame, text=self.t("cancel"), command=on_cancel, width=12)
            cancel_btn.pack(side=tk.RIGHT)
            
            # Bind keys
            entry.bind('<Return>', on_ok)
            entry.bind('<Escape>', on_cancel)
            dialog.bind('<Return>', on_ok)
            dialog.bind('<Escape>', on_cancel)
            
            # Focus on top
            dialog.lift()
            dialog.focus_force()
            
            # Wait for dialog
            self.root.wait_window(dialog)
            
            # Process result
            new_name = result['name']
            if new_name and new_name != old_name:
                directory = os.path.dirname(file_path)
                new_path = os.path.join(directory, new_name)
                
                if os.path.exists(new_path):
                    messagebox.showerror(self.t("error"), self.t("file_exists"))
                    return
                
                os.rename(file_path, new_path)
                self.update_status(self.t("rename_success").format(new_name))
                
                # Update tree item
                for item in self.tree.get_children():
                    if self.tree.item(item)['values'][-1] == file_path:
                        is_checked = self.checked_items.get(item, False)
                        checkbox = self.check_images['checked'] if is_checked else self.check_images['unchecked']
                        new_text = f"{checkbox} {new_name}"
                        self.tree.item(item, text=new_text)
                        values = list(self.tree.item(item)['values'])
                        values[-1] = new_path
                        self.tree.item(item, values=values)
                        break
        except Exception as e:
            messagebox.showerror(self.t("rename_failed"), str(e))
    
    def delete_file(self, file_path: str):
        """Delete file"""
        try:
            if messagebox.askyesno(self.t("delete"), self.t("confirm_delete")):
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                
                self.update_status(self.t("delete_success").format(os.path.basename(file_path)))
                
                # Remove from tree instead of full search
                for item in self.tree.get_children():
                    if self.tree.item(item)['values'][-1] == file_path:
                        self.tree.delete(item)
                        self.update_results_label()
                        break
        except Exception as e:
            messagebox.showerror(self.t("delete_failed"), str(e))
    
    def create_shortcut(self, file_path: str):
        """Create shortcut"""
        try:
            if sys.platform == 'win32':
                import win32com.client
                
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                shortcut_name = os.path.splitext(os.path.basename(file_path))[0] + ".lnk"
                shortcut_path = os.path.join(desktop, shortcut_name)
                
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.Targetpath = file_path
                shortcut.WorkingDirectory = os.path.dirname(file_path)
                shortcut.save()
                
                self.update_status(self.t("shortcut_created").format(shortcut_name))
            else:
                messagebox.showinfo(self.t("error"), self.t("shortcut_not_supported"))
        except Exception as e:
            messagebox.showerror(self.t("shortcut_failed"), str(e))
    
    def copy_path(self, file_path: str):
        """Copy file path to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(file_path)
        self.update_status(self.t("copied_path"))
    
    def show_properties(self, file_path: str):
        """Show file properties"""
        try:
            file_item = FileItem(file_path)
            
            props_window = tk.Toplevel(self.root)
            props_window.title(self.t("file_properties"))
            props_window.geometry("500x300")
            props_window.resizable(False, False)
            self.set_window_icon(props_window)
            
            props_frame = ttk.Frame(props_window, padding="20")
            props_frame.pack(fill=tk.BOTH, expand=True)
            
            properties = [
                (self.t("name").rstrip(':') + ":", file_item.name),
                (self.t("type") + ":", file_item.get_type()),
                (self.t("location") + ":", os.path.dirname(file_path)),
                (self.t("size") + ":", file_item.get_size_str()),
                (self.t("modified_date") + ":", file_item.modified.strftime("%Y-%m-%d %H:%M:%S")),
                (self.t("full_path") + ":", file_path)
            ]
            
            for i, (label, value) in enumerate(properties):
                ttk.Label(props_frame, text=label, font=('', 10, 'bold')).grid(row=i, column=0, sticky=tk.W, pady=5, padx=(0, 10))
                ttk.Label(props_frame, text=value, wraplength=350).grid(row=i, column=1, sticky=tk.W, pady=5)
            
            ttk.Button(props_frame, text=self.t("close"), command=props_window.destroy).grid(row=len(properties), column=0, columnspan=2, pady=(20, 0))
            
        except Exception as e:
            messagebox.showerror(self.t("error"), f"Failed to show properties:\n{str(e)}")
    
    def copy_files_to(self, file_paths: list):
        """Copy multiple files to selected directory"""
        if not file_paths:
            return
        
        try:
            # Create dialog with icon
            dialog = tk.Toplevel(self.root)
            dialog.withdraw()
            self.set_window_icon(dialog)
            dialog.destroy()
            
            destination = filedialog.askdirectory(
                title=self.t("select_destination"),
                initialdir=os.path.dirname(file_paths[0])
            )
            
            if destination:
                success_count = 0
                skip_count = 0
                error_count = 0
                
                for file_path in file_paths:
                    try:
                        filename = os.path.basename(file_path)
                        dest_path = os.path.join(destination, filename)
                        
                        # Check if file exists
                        if os.path.exists(dest_path):
                            result = messagebox.askyesnocancel(
                                self.t("file_exists"), 
                                f"{filename}\n\n{self.t('overwrite_confirm')}"
                            )
                            if result is None:  # Cancel
                                break
                            elif not result:  # No
                                skip_count += 1
                                continue
                        
                        shutil.copy2(file_path, dest_path)
                        success_count += 1
                        self.update_status(f"Copying {success_count}/{len(file_paths)}: {filename}")
                        
                    except Exception as e:
                        error_count += 1
                        print(f"Error copying {file_path}: {e}")
                
                # Show summary
                message = f"{self.t('copy_complete')}\n\n"
                message += f"{self.t('success')}: {success_count}\n"
                if skip_count > 0:
                    message += f"{self.t('skipped')}: {skip_count}\n"
                if error_count > 0:
                    message += f"{self.t('errors')}: {error_count}\n"
                message += f"\n{self.t('destination')}: {destination}"
                
                messagebox.showinfo(self.t("copy_complete"), message)
                
        except Exception as e:
            messagebox.showerror(self.t("error"), f"Copy failed:\n{str(e)}")
    
    def move_files_to(self, file_paths: list):
        """Move multiple files to selected directory"""
        if not file_paths:
            return
        
        try:
            dialog = tk.Toplevel(self.root)
            dialog.withdraw()
            self.set_window_icon(dialog)
            dialog.destroy()
            
            destination = filedialog.askdirectory(
                title=self.t("select_destination"),
                initialdir=os.path.dirname(file_paths[0])
            )
            
            if destination:
                success_count = 0
                skip_count = 0
                error_count = 0
                
                for file_path in file_paths:
                    try:
                        filename = os.path.basename(file_path)
                        dest_path = os.path.join(destination, filename)
                        
                        if os.path.exists(dest_path):
                            result = messagebox.askyesnocancel(
                                self.t("file_exists"), 
                                f"{filename}\n\n{self.t('overwrite_confirm')}"
                            )
                            if result is None:
                                break
                            elif not result:
                                skip_count += 1
                                continue
                        
                        shutil.move(file_path, dest_path)
                        success_count += 1
                        self.update_status(f"Moving {success_count}/{len(file_paths)}: {filename}")
                        
                    except Exception as e:
                        error_count += 1
                        print(f"Error moving {file_path}: {e}")
                
                message = f"{self.t('move_complete')}\n\n"
                message += f"{self.t('success')}: {success_count}\n"
                if skip_count > 0:
                    message += f"{self.t('skipped')}: {skip_count}\n"
                if error_count > 0:
                    message += f"{self.t('errors')}: {error_count}\n"
                message += f"\n{self.t('destination')}: {destination}"
                
                messagebox.showinfo(self.t("move_complete"), message)
                
        except Exception as e:
            messagebox.showerror(self.t("error"), f"Move failed:\n{str(e)}")
    
    def add_files_to_startup(self, file_paths: list):
        """Add multiple file shortcuts to Windows startup folder"""
        if sys.platform != 'win32':
            messagebox.showerror(self.t("error"), "This feature is only available on Windows")
            return
        
        if not file_paths:
            return
        
        try:
            import win32com.client
            
            startup_folder = os.path.join(
                os.environ['APPDATA'],
                r'Microsoft\Windows\Start Menu\Programs\Startup'
            )
            
            success_count = 0
            skip_count = 0
            error_count = 0
            
            for file_path in file_paths:
                try:
                    filename = os.path.splitext(os.path.basename(file_path))[0]
                    shortcut_path = os.path.join(startup_folder, f"{filename}.lnk")
                    
                    if os.path.exists(shortcut_path):
                        result = messagebox.askyesnocancel(
                            self.t("already_exists"),
                            f"{filename}\n\n{self.t('replace_startup_shortcut')}"
                        )
                        if result is None:
                            break
                        elif not result:
                            skip_count += 1
                            continue
                    
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(shortcut_path)
                    shortcut.TargetPath = file_path
                    shortcut.WorkingDirectory = os.path.dirname(file_path)
                    shortcut.IconLocation = file_path
                    shortcut.save()
                    
                    success_count += 1
                    self.update_status(f"Adding to startup {success_count}/{len(file_paths)}: {filename}")
                    
                except Exception as e:
                    error_count += 1
                    print(f"Error adding {file_path} to startup: {e}")
            
            message = f"{self.t('startup_complete')}\n\n"
            message += f"{self.t('success')}: {success_count}\n"
            if skip_count > 0:
                message += f"{self.t('skipped')}: {skip_count}\n"
            if error_count > 0:
                message += f"{self.t('errors')}: {error_count}"
            
            messagebox.showinfo(self.t("startup_complete"), message)
            
        except ImportError:
            messagebox.showerror(
                self.t("error"),
                "pywin32 module required.\nInstall with: pip install pywin32"
            )
        except Exception as e:
            messagebox.showerror(self.t("error"), f"Failed to add to startup:\n{str(e)}")
    
    def open_startup_folder(self):
        """Open Windows startup folder"""
        if sys.platform != 'win32':
            messagebox.showerror(self.t("error"), "This feature is only available on Windows")
            return
        
        try:
            startup_folder = os.path.join(
                os.environ['APPDATA'],
                r'Microsoft\Windows\Start Menu\Programs\Startup'
            )
            os.startfile(startup_folder)
            self.update_status(self.t("opened_startup_folder"))
        except Exception as e:
            messagebox.showerror(self.t("error"), f"Failed to open startup folder:\n{str(e)}")
    
    def execute_selected(self):
        """Execute all selected files"""
        checked_files = [
            self.tree.item(item_id, "values")[3]
            for item_id, checked in self.checked_items.items()
            if checked
        ]
        
        if not checked_files:
            messagebox.showinfo(self.t("no_selection"), self.t("select_files_msg"))
            return
        
        if not messagebox.askyesno(self.t("confirm_execution"), self.t("execute_confirm").format(len(checked_files))):
            return
        
        thread = threading.Thread(target=self.execute_files_sequentially, args=(checked_files,), daemon=True)
        thread.start()
    
    def execute_files_sequentially(self, file_paths: List[str]):
        """Execute files sequentially"""
        for i, file_path in enumerate(file_paths, 1):
            try:
                self.root.after(0, self.update_status, self.t("executing").format(i, len(file_paths), os.path.basename(file_path)))
                
                if sys.platform == 'win32':
                    os.startfile(file_path)
                else:
                    subprocess.Popen(['xdg-open', file_path])
                
                import time
                time.sleep(0.5)
                
            except Exception as e:
                self.root.after(0, messagebox.showerror, self.t("execution_error"), f"Failed to execute {file_path}:\n{str(e)}")
        
        self.root.after(0, self.update_status, self.t("completed_executing").format(len(file_paths)))
    
    def clear_results(self):
        """Clear search results"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.search_results.clear()
        self.checked_items.clear()
        self.results_label.config(text=self.t("results") + " 0")
        self.update_status(self.t("results_cleared"))
    
    def update_results_label(self):
        """Update results count label"""
        count = len(self.tree.get_children())
        self.results_label.config(text=self.t("results") + f" {count}")
    
    def export_results(self):
        """Export search results to CSV"""
        if not self.search_results:
            messagebox.showinfo(self.t("no_results"), self.t("no_results_export"))
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            title=self.t("export_results")
        )
        
        if not file_path:
            return
        
        try:
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([self.t("name").rstrip(':'), self.t("type"), self.t("modified_date"), 
                               self.t("size"), self.t("full_path")])
                
                for file_item in self.search_results:
                    writer.writerow([
                        file_item.name,
                        file_item.get_type(),
                        file_item.modified.strftime("%Y-%m-%d %H:%M:%S"),
                        file_item.get_size_str(),
                        file_item.path
                    ])
            
            messagebox.showinfo(self.t("export_complete"), self.t("exported_to").format(file_path))
            self.update_status(f"Exported {len(self.search_results)} results to CSV")
            
        except Exception as e:
            messagebox.showerror(self.t("export_error"), f"Failed to export results:\n{str(e)}")
    
    def update_status(self, message: str):
        """Update status bar"""
        self.status_label.config(text=message)
    
    def change_language(self, lang_code: str, lang_display: str = None):
        """Change application language and update UI immediately"""
        if lang_display is None:
            lang_display = lang_code
            
        old_language = self.current_language
        old_language_code = self.current_language_code if hasattr(self, 'current_language_code') else 'en'
        
        self.current_language = lang_display
        self.current_language_code = lang_code
        
        # Reset to default translations first
        self.translations = self.DEFAULT_TRANSLATIONS.copy()
        
        # Try to load language file
        success = False
        lang_file = f"lang_{lang_code}.ini"
        lang_path = resource_path(os.path.join("language", lang_file))
        
        if lang_code != "en":
            success = self.load_language_file_by_code(lang_code)
        else:
            success = True  # English is default
        
        if success:
            self.save_settings()
            
            # Show bilingual notification message FIRST (before UI update)
            if lang_code == "ko":
                message = (
                    "언어가 한국어로 변경되었습니다.\n"
                    "일부 UI 요소는 프로그램을 재시작하면 완전히 적용됩니다.\n\n"
                    "Language changed to Korean.\n"
                    "Some UI elements will be fully applied after restarting the program."
                )
            else:
                message = (
                    "Language changed to English.\n"
                    "Some UI elements will be fully applied after restarting the program.\n\n"
                    "언어가 영어로 변경되었습니다.\n"
                    "일부 UI 요소는 프로그램을 재시작하면 완전히 적용됩니다."
                )
            
            # Show message BEFORE updating UI
            messagebox.showinfo("Language Changed / 언어 변경", message)
            
            # Update all UI text (with error handling)
            try:
                self.update_ui_text()
            except Exception as e:
                pass  # Silently continue if UI update fails
        else:
            # Revert to old language
            self.current_language = old_language
            self.current_language_code = old_language_code
            if old_language_code != "en":
                self.load_language_file_by_code(old_language_code)
            
            # Show detailed error with paths
            error_msg = (
                f"Failed to load language file for {lang_display}.\n\n"
                f"Looking for: {lang_file}\n"
                f"Search path: {lang_path}\n"
                f"File exists: {os.path.exists(lang_path)}\n\n"
                f"Please place the language file in the same folder as the program.\n\n"
                f"Current directory: {os.getcwd()}\n"
                f"Executable directory: {os.path.dirname(sys.executable)}\n"
                f"Script directory: {os.path.dirname(os.path.abspath(__file__))}"
            )
            
            messagebox.showerror("Language Error", error_msg)
    
    def update_ui_text(self):
        """Update all UI text with current language"""
        # Update window title
        self.root.title(self.t("title"))
        
        # Update menu
        self.menu_bar.entryconfig(0, label=self.t("menu_view"))
        self.menu_bar.entryconfig(1, label=self.t("menu_language"))
        self.menu_bar.entryconfig(2, label=self.t("menu_help"))
        
        # Update buttons (need to recreate main UI elements)
        # For simplicity, show message that some elements need restart
        # Or we can store all widget references and update them
        
        # Update status
        self.update_status(self.t("ready"))
    
    def open_github(self):
        """Open GitHub repository"""
        import webbrowser
        webbrowser.open("https://github.com/gloriouslegacy/ezSLauncher/releases")
        self.update_status(self.t("opening_github"))
    
    def show_about(self):
        """Show about dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title(self.t("about_title"))
        about_window.geometry("400x250")
        about_window.resizable(False, False)
        self.set_window_icon(about_window)
        
        about_frame = ttk.Frame(about_window, padding="20")
        about_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(about_frame, text=self.t("title"), font=('', 16, 'bold')).pack(pady=(0, 10))
        ttk.Label(about_frame, text=self.t("description"), justify=tk.CENTER).pack(pady=(0, 10))
        ttk.Label(about_frame, text=self.t("created_by") + "gloriouslegacy").pack(pady=(0, 5))
        ttk.Label(about_frame, text=self.t("copyright")).pack(pady=(0, 20))
        
        ttk.Button(about_frame, text=self.t("close"), command=about_window.destroy).pack()
    
    def check_for_updates(self):
        """Check for updates from GitHub"""
        def check_thread():
            try:
                self.update_status(self.t("checking_update"))
                
                # Get latest release info from GitHub
                req = urllib.request.Request(GITHUB_API_URL)
                req.add_header('User-Agent', 'ezSLauncher')
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                
                latest_version = data['tag_name'].lstrip('v')
                
                # Compare versions
                if self.compare_versions(latest_version, CURRENT_VERSION) > 0:
                    # Update available
                    self.root.after(0, lambda: self.show_update_dialog(data, latest_version))
                else:
                    # Already up to date
                    self.root.after(0, lambda: messagebox.showinfo(
                        self.t("no_update"),
                        self.t("no_update_msg").format(CURRENT_VERSION)
                    ))
                    self.update_status(self.t("ready"))
            
            except urllib.error.URLError as e:
                self.root.after(0, lambda: messagebox.showerror(
                    self.t("update_error"),
                    self.t("update_error_msg").format(str(e))
                ))
                self.update_status(self.t("ready"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    self.t("update_error"),
                    self.t("update_error_msg").format(str(e))
                ))
                self.update_status(self.t("ready"))
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def check_for_updates_silent(self):
        """Check for updates silently on startup (no error messages)"""
        def check_thread():
            try:
                # Get latest release info from GitHub
                req = urllib.request.Request(GITHUB_API_URL)
                req.add_header('User-Agent', 'ezSLauncher')
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                
                latest_version = data['tag_name'].lstrip('v')
                
                # Compare versions
                if self.compare_versions(latest_version, CURRENT_VERSION) > 0:
                    # Update available - show dialog
                    self.root.after(0, lambda: self.show_update_dialog(data, latest_version))
                # If no update or error, do nothing (silent)
            
            except:
                # Silent failure - don't show error on startup
                pass
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings using string comparison.
        This ensures v0.2.9 > v0.2.89 and v0.2.8 > v0.2.71 as requested.
        Returns: 1 if v1 > v2, 0 if equal, -1 if v1 < v2
        """
        # Normalize strings (remove v, whitespace)
        s1 = v1.lower().lstrip('v').strip()
        s2 = v2.lower().lstrip('v').strip()
        
        if s1 > s2:
            return 1
        elif s1 < s2:
            return -1
        return 0
    
    def show_update_dialog(self, release_data, latest_version):
        """Show update available dialog"""
        result = messagebox.askyesno(
            self.t("update_available"),
            self.t("update_available_msg").format(latest_version, CURRENT_VERSION)
        )
        
        if result:
            self.download_and_install_update(release_data)
        else:
            self.update_status(self.t("ready"))
    
    def download_and_install_update(self, release_data):
        """Download and install update"""
        def download_thread():
            try:
                # Determine which asset to download
                assets = release_data.get('assets', [])
                
                # Detect installation type
                # Portable: executable name contains "Portable"
                # Installer: installed via setup (check for uninstall registry or specific paths)
                exe_name = os.path.basename(sys.executable) if getattr(sys, 'frozen', False) else ""
                is_portable = 'Portable' in exe_name
                
                download_url = None
                asset_name = None
                sha256_sum = None
                
                # Look for appropriate download
                if is_portable:
                    # Look for portable zip
                    for asset in assets:
                        if 'Portable.zip' in asset['name']:
                            download_url = asset['browser_download_url']
                            asset_name = asset['name']
                            break
                else:
                    # Look for setup installer (for both installed and manual versions)
                    for asset in assets:
                        if 'Setup.exe' in asset['name']:
                            download_url = asset['browser_download_url']
                            asset_name = asset['name']
                            break
                
                if not download_url:
                    raise Exception("Could not find appropriate update file")
                
                # Get SHA256 from release body
                body = release_data.get('body', '')
                
                # Different SHA256 patterns for different file types
                if is_portable:
                    # Look for Portable Version SHA256
                    sha_match = re.search(r'\*\*Portable Version.*?```\s*([a-fA-F0-9]{64})\s*```', body, re.DOTALL)
                else:
                    # Look for Installer Version SHA256
                    sha_match = re.search(r'\*\*Installer Version.*?```\s*([a-fA-F0-9]{64})\s*```', body, re.DOTALL)
                
                if sha_match:
                    sha256_sum = sha_match.group(1).strip().lower()
                
                # Download file
                self.update_status(self.t("downloading_update"))
                download_path = os.path.join(CONFIG_DIR, asset_name)
                
                def reporthook(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = min(100, int(block_num * block_size * 100 / total_size))
                        self.root.after(0, lambda: self.update_status(
                            self.t("download_progress").format(percent)
                        ))
                
                urllib.request.urlretrieve(download_url, download_path, reporthook=reporthook)
                
                # Verify checksum if available
                if sha256_sum:
                    self.update_status(self.t("verifying_checksum"))
                    file_hash = self.calculate_sha256(download_path)
                    
                    if file_hash != sha256_sum:
                        os.remove(download_path)
                        raise Exception(self.t("checksum_failed"))
                
                # Create backup
                self.update_status(self.t("creating_backup"))
                if not self.create_backup():
                    os.remove(download_path)
                    raise Exception(self.t("backup_failed"))
                
                # Install update
                self.root.after(0, lambda: self.install_update(download_path, is_portable))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    self.t("update_error"),
                    self.t("update_error_msg").format(str(e))
                ))
                self.update_status(self.t("ready"))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def calculate_sha256(self, filepath):
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def create_backup(self):
        """Create backup of current executable and config"""
        try:
            backup_dir = os.path.join(CONFIG_DIR, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup executable
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                exe_name = os.path.basename(exe_path)
                backup_exe = os.path.join(backup_dir, exe_name)
                shutil.copy2(exe_path, backup_exe)
            
            # Config is already in CONFIG_DIR, no need to backup
            
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False
    
    def install_update(self, update_path, is_portable):
        """Install the downloaded update"""
        try:
            if is_portable:
                # For portable, use updater.exe
                exe_dir = os.path.dirname(sys.executable)
                exe_name = os.path.basename(sys.executable)
                
                # Look for updater.exe in same directory
                updater_path = os.path.join(exe_dir, "updater.exe")
                
                if not os.path.exists(updater_path):
                    # Fallback: try to extract updater from zip
                    import zipfile
                    try:
                        with zipfile.ZipFile(update_path, 'r') as zip_ref:
                            # Check if updater.exe is in the zip
                            if 'updater.exe' in zip_ref.namelist():
                                zip_ref.extract('updater.exe', exe_dir)
                                updater_path = os.path.join(exe_dir, "updater.exe")
                            else:
                                raise Exception("updater.exe not found in update package")
                    except Exception as e:
                        raise Exception(f"updater.exe not found. Please download the complete package.\nError: {str(e)}")
                
                # Launch updater.exe with arguments
                # updater.exe <update_file> <target_dir> <exe_name>
                subprocess.Popen(
                    [updater_path, update_path, exe_dir, exe_name],
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
                )
                
                # Close application immediately without message
                self.root.quit()
                
            else:
                # For installer/manual versions:
                # 1. Download Setup.exe
                # 2. Create a batch file to wait for setup completion and restart app
                # 3. Run Setup.exe with /VERYSILENT flag
                # 4. Batch file will restart the application automatically
                
                # Get installation path (try to detect from registry or use current location)
                exe_path = sys.executable if getattr(sys, 'frozen', False) else None
                
                if exe_path:
                    # Create auto-restart batch file
                    restart_script = os.path.join(CONFIG_DIR, "restart_after_update.bat")
                    
                    script_content = f"""@echo off
echo Waiting for installer to complete...
:WAIT
timeout /t 2 /nobreak > nul
tasklist /FI "IMAGENAME eq {os.path.basename(update_path)}" 2>NUL | find /I /N "{os.path.basename(update_path)}">NUL
if "%ERRORLEVEL%"=="0" goto WAIT

echo Starting application...
timeout /t 1 /nobreak > nul
start "" "{exe_path}"

echo Cleaning up...
del "{update_path}"
del "%~f0"
"""
                    
                    with open(restart_script, 'w') as f:
                        f.write(script_content)
                    
                    # Run setup
                    subprocess.Popen([update_path, '/VERYSILENT', '/NORESTART'])
                    
                    # Run restart script
                    subprocess.Popen(['cmd', '/c', restart_script], 
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    # Fallback: just run setup without auto-restart
                    subprocess.Popen([update_path, '/VERYSILENT', '/NORESTART'])
                
                messagebox.showinfo(
                    self.t("update_complete"),
                    self.t("update_complete_msg")
                )
                
                self.root.quit()
                
        except Exception as e:
            messagebox.showerror(
                self.t("update_error"),
                self.t("update_error_msg").format(str(e))
            )
            self.update_status(self.t("ready"))
    
    def schedule_save_settings(self):
        """Schedule save settings with debounce (wait 500ms after last change)"""
        if self.save_timer:
            self.root.after_cancel(self.save_timer)
        self.save_timer = self.root.after(500, self.save_settings)
    
    def save_settings(self):
        """Save settings to config file"""
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
        default_dir = os.path.expanduser("~")
        
        if self.config:
            self.name_filter.insert(0, self.config.get("name_filter", ""))
            self.ext_filter.insert(0, self.config.get("ext_filter", ""))
            self.path_filter.insert(0, self.config.get("path_filter", ""))
            self.search_dir.insert(0, self.config.get("search_dir", default_dir))
            self.recursive_var.set(self.config.get("recursive", True))
            
            # Load regex state and show/hide tip accordingly
            regex_state = self.config.get("use_regex", False)
            self.regex_var.set(regex_state)
            if regex_state:
                self.toggle_regex_tip()
        else:
            self.search_dir.insert(0, default_dir)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = FileSearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()