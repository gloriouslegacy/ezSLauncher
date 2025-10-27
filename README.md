# File Search & Launcher

Advanced file search and execution application for Windows with GUI interface.

## Features

### Core Features
- **Advanced Search Filters**: Search by name, extension, and path
- **Recursive Directory Search**: Search in subdirectories
- **Multiple File Selection**: Checkbox-based selection system
- **Sequential Execution**: Execute multiple files in order
- **Context Menu**: Right-click menu with Windows Explorer-like options
- **Administrator Execution**: Run files with elevated privileges
- **Persistent Settings**: Automatically saves and loads search preferences

### User Interface
- **Modern GUI**: Clean and intuitive Tkinter interface
- **Treeview Results**: Display files with type, date, size, and path
- **Checkbox Selection**: Visual checkbox indicators (☐/☑)
- **Progress Indicator**: Shows search progress
- **Status Bar**: Real-time status updates
- **Custom Icons**: Support for .ico and .png icons

### Execution Options
- **Double-click**: Normal file execution (like Windows Explorer)
- **Right-click Menu**:
  - Open
  - Run as Administrator
  - Open File Location
  - Copy Path
  - Properties

### Background Processing
- **Threaded Search**: Non-blocking UI during search
- **Threaded Execution**: Sequential file execution in background
- **Real-time Updates**: Progress feedback during operations

## Installation

### Prerequisites
- Windows 10/11
- Python 3.7 or higher

### Setup
1. Install Python if not already installed (download from python.org)

2. Create project directory:
```bash
mkdir FileSearchApp
cd FileSearchApp
```

3. Save the script as `file_search_launcher.py`

4. Create icon directory (optional):
```bash
mkdir icon
```

5. Add your icons to the icon folder:
   - `icon/icon.ico` (Windows icon format)
   - `icon/icon.png` (fallback PNG format)

### No Additional Dependencies Required
The application uses only Python standard library:
- tkinter (included with Python on Windows)
- os, sys, json, subprocess, threading, pathlib, datetime

## Usage

### Running the Application
```bash
python file_search_launcher.py
```

Or double-click the `file_search_launcher.py` file in Windows Explorer.

### Creating a Shortcut
1. Right-click on `file_search_launcher.py`
2. Select "Create shortcut"
3. Right-click the shortcut → Properties
4. Change "Target" to: `pythonw.exe "C:\path\to\file_search_launcher.py"`
5. Set icon if desired

### Basic Workflow

#### 1. Set Search Filters
- **Name**: Filter by filename (partial match)
- **Extension**: Filter by file extension (e.g., .txt, .exe)
- **Path Contains**: Filter by path content
- **All filters work together** (AND logic)

#### 2. Select Search Directory
- Click "Browse..." button
- Navigate to desired folder
- Select "Include Subdirectories" for recursive search

#### 3. Execute Search
- Click "🔍 Search" button
- Wait for results to appear
- View results count in status bar

#### 4. Work with Results
- **Check files**: Click checkbox or press Space
- **Select All**: Click "☑ Select All"
- **Select None**: Click "☐ Select None"
- **Double-click**: Execute single file
- **Right-click**: Show context menu

#### 5. Execute Selected Files
- Check desired files
- Click "▶ Execute Selected"
- Confirm execution
- Files will open sequentially

### Context Menu Options

#### Open
Normal file execution using default associated program

#### Run as Administrator
Execute with elevated privileges (shows UAC prompt)

#### Open File Location
Open Windows Explorer at file location with file selected

#### Copy Path
Copy full file path to clipboard

#### Properties
Show detailed file information:
- Name
- Type
- Location
- Size
- Modified date
- Full path

### Tips & Tricks

#### Filter Examples
```
Name: "report" → Finds: report.pdf, annual_report.docx, etc.
Extension: ".py" → Finds: All Python files
Path: "documents" → Finds: Files with "documents" in path
```

#### Combining Filters
```
Name: "invoice"
Extension: ".pdf"
Path: "2025"
→ Finds: invoice*.pdf files in paths containing "2025"
```

#### Keyboard Shortcuts
- **Space**: Toggle checkbox on selected item
- **Double-click**: Execute file
- **Right-click**: Context menu

#### Settings Persistence
All settings are automatically saved:
- Search filters
- Search directory
- Recursive option

Settings are stored in `app_config.json` and restored on next launch.

## Configuration File

The application creates `app_config.json` to store settings:

```json
{
    "name_filter": "document",
    "ext_filter": ".pdf",
    "path_filter": "",
    "search_dir": "C:\\Users\\YourName\\Documents",
    "recursive": true
}
```

You can manually edit this file when the application is closed.

## Troubleshooting

### UAC Prompts
When running as administrator, Windows will show UAC prompt. This is normal security behavior.

### Permission Errors
Some system directories require administrator privileges. The application will skip inaccessible files.

### Icon Not Showing
- Verify icon files exist in `./icon/` directory
- Supported formats: .ico, .png
- Icon path is relative to script location

### Files Not Executing
- Verify file associations are set in Windows
- Try right-click → Open
- Check if file is blocked (Properties → Unblock)

### Search Too Slow
- Disable "Include Subdirectories" for faster search
- Use more specific filters
- Search in smaller directories

## Advanced Features

### Background Execution
All file operations run in separate threads:
- UI remains responsive during search
- Multiple files execute sequentially
- Progress updates in real-time

### Error Handling
- Permission errors are gracefully handled
- Failed executions show error messages
- Invalid paths are validated

### Performance
- Efficient file scanning
- Lazy loading of file statistics
- Memory-efficient result storage

## System Requirements

- **OS**: Windows 10/11 (primary), Linux/macOS (limited support)
- **Python**: 3.7+
- **RAM**: 100MB minimum
- **Disk**: 1MB for application + space for results

## Security Notes

### Administrator Execution
- UAC prompt will appear when needed
- Only run trusted files as administrator
- Administrator mode is optional

### File Execution
- Application uses Windows default file associations
- No files are modified or deleted
- Always review selected files before execution

## Building Executable (Optional)

To create a standalone .exe file:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon/icon.ico file_search_launcher.py
```

The executable will be in the `dist` folder.

## License

This application is provided as-is for educational and personal use.

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Verify Python installation
3. Check file permissions
4. Review error messages in dialogs

## Version History

### v1.0.0
- Initial release
- Core search functionality
- Context menu integration
- Settings persistence
- Background execution
- UAC support

## Future Enhancements (Possible)
- File preview
- Drag and drop support
- Export results to CSV
- Custom execution commands
- Search history
- Favorites/bookmarks
- Dark theme
- Multi-language support
# ezSLauncher
