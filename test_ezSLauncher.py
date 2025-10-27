"""
Test Utility Script for File Search & Launcher
Creates sample files and folders for testing
"""

import os
from pathlib import Path


def create_test_structure():
    """Create a sample directory structure for testing"""
    
    base_dir = Path("test_files")
    base_dir.mkdir(exist_ok=True)
    
    # Create test directories
    dirs = [
        "test_files/documents/2024",
        "test_files/documents/2025",
        "test_files/programs",
        "test_files/images",
        "test_files/scripts",
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Create test files
    test_files = [
        # Documents
        ("test_files/documents/2024/report_q1.txt", "Q1 Report 2024"),
        ("test_files/documents/2024/report_q2.txt", "Q2 Report 2024"),
        ("test_files/documents/2025/report_q1.txt", "Q1 Report 2025"),
        ("test_files/documents/2025/annual_report.txt", "Annual Report 2025"),
        ("test_files/documents/invoice_2024.txt", "Invoice 2024"),
        
        # Programs (text files for testing)
        ("test_files/programs/app_installer.txt", "Application Installer"),
        ("test_files/programs/tool_v1.txt", "Tool Version 1"),
        ("test_files/programs/tool_v2.txt", "Tool Version 2"),
        
        # Images (text files as placeholders)
        ("test_files/images/photo1.jpg.txt", "Photo 1"),
        ("test_files/images/photo2.png.txt", "Photo 2"),
        ("test_files/images/screenshot.png.txt", "Screenshot"),
        
        # Scripts
        ("test_files/scripts/backup.py.txt", "# Backup Script\nprint('Backup complete')"),
        ("test_files/scripts/deploy.py.txt", "# Deploy Script\nprint('Deploy complete')"),
        ("test_files/scripts/test.py.txt", "# Test Script\nprint('Tests passed')"),
        
        # Root level
        ("test_files/readme.txt", "This is a test directory structure"),
        ("test_files/config.ini", "[Settings]\nversion=1.0"),
    ]
    
    for file_path, content in test_files:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    print(f"✓ Created test directory structure in '{base_dir.absolute()}'")
    print(f"✓ Created {len(test_files)} test files")
    print(f"✓ Created {len(dirs)} directories")
    print("\nTest files ready for searching!")
    print(f"\nUse this path in the application: {base_dir.absolute()}")


def cleanup_test_structure():
    """Remove test directory structure"""
    import shutil
    base_dir = Path("test_files")
    
    if base_dir.exists():
        shutil.rmtree(base_dir)
        print(f"✓ Removed test directory structure")
    else:
        print("✗ Test directory not found")


def show_usage():
    """Show usage information"""
    print("""
Test Utility for File Search & Launcher
========================================

Usage:
    python test_utility.py create    - Create test file structure
    python test_utility.py cleanup   - Remove test file structure
    python test_utility.py help      - Show this help message

Examples:
    1. Create test files:
       python test_utility.py create

    2. Use the created 'test_files' directory in the main application

    3. Test various filters:
       - Name: "report" → Find all report files
       - Extension: ".txt" → Find all text files
       - Path: "2025" → Find files in 2025 folders

    4. Clean up when done:
       python test_utility.py cleanup
    """)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        show_usage()
    elif sys.argv[1] == "create":
        create_test_structure()
    elif sys.argv[1] == "cleanup":
        cleanup_test_structure()
    elif sys.argv[1] == "help":
        show_usage()
    else:
        print(f"Unknown command: {sys.argv[1]}")
        show_usage()
