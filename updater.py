"""
ezSLauncher Updater
Handles file replacement after download
"""

import os
import sys
import time
import shutil
import subprocess
import zipfile
from pathlib import Path

def main():
    """Main updater logic"""
    if len(sys.argv) < 4:
        print("Usage: updater.exe <update_file> <target_dir> <exe_name>")
        sys.exit(1)
    
    update_file = sys.argv[1]  # Downloaded update file (zip or exe)
    target_dir = sys.argv[2]   # Target installation directory
    exe_name = sys.argv[3]     # Executable name to restart
    
    try:
        print("ezSLauncher Updater")
        print(f"Update file: {update_file}")
        print(f"Target directory: {target_dir}")
        print(f"Executable: {exe_name}")
        print("\nWaiting for main application to close...")
        
        # Wait for main app to close
        time.sleep(2)
        
        # Determine update type
        if update_file.endswith('.zip'):
            # Portable version - extract and replace
            print("Installing portable update...")
            install_portable_update(update_file, target_dir, exe_name)
        elif update_file.endswith('.exe'):
            # Installer version - run silent install
            print("Running installer...")
            install_setup_update(update_file)
        else:
            print(f"Unknown update file type: {update_file}")
            sys.exit(1)
        
        print("Update completed successfully!")
        
    except Exception as e:
        print(f"Update failed: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

def install_portable_update(zip_file, target_dir, exe_name):
    """Install portable version from zip"""
    temp_dir = os.path.join(os.path.dirname(zip_file), "update_temp")
    
    try:
        # Extract zip to temp directory
        print("Extracting update...")
        os.makedirs(temp_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Debug: List all extracted files
        print(f"\n=== Extracted files ===")
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), temp_dir)
                print(f"  {rel_path}")
        print("")
        
        # Find the portable executable in extracted files
        exe_found = False
        portable_exe = None
        
        print(f"Looking for portable executable (target: {exe_name})...")
        
        # Search in all directories
        for root, dirs, files in os.walk(temp_dir):
            print(f"Checking directory: {root}")
            for file in files:
                print(f"  Found file: {file}")
                
                # Look for portable executable
                # Case 1: Exact match with current exe name
                if file == exe_name:
                    portable_exe = file
                    source_file = os.path.join(root, file)
                    print(f"✓ Found exact match: {file}")
                # Case 2: Any .exe with 'Portable' in name
                elif file.endswith('.exe') and 'Portable' in file:
                    portable_exe = file
                    source_file = os.path.join(root, file)
                    print(f"✓ Found portable exe: {file}")
                
                # If we found an exe, process it
                if portable_exe:
                    target_file = os.path.join(target_dir, exe_name)
                    
                    print(f"\n=== Starting Update ===")
                    print(f"Source: {source_file}")
                    print(f"Target: {target_file}")
                    
                    # Backup old executable
                    backup_file = target_file + ".backup"
                    if os.path.exists(target_file):
                        print(f"Creating backup: {backup_file}")
                        try:
                            # Force close if file is locked
                            if os.path.exists(backup_file):
                                os.remove(backup_file)
                            shutil.copy2(target_file, backup_file)
                            print(f"✓ Backup created")
                        except Exception as e:
                            print(f"Warning: Could not create backup: {e}")
                    
                    # Replace executable
                    print(f"Replacing {exe_name}...")
                    try:
                        # Remove target if exists
                        if os.path.exists(target_file):
                            os.remove(target_file)
                        shutil.copy2(source_file, target_file)
                        print(f"✓ Successfully replaced executable")
                        exe_found = True
                    except Exception as e:
                        print(f"✗ Failed to replace executable: {e}")
                        raise e
                    
                    # Copy language folder
                    lang_source = os.path.join(temp_dir, "language")
                    lang_target = os.path.join(target_dir, "language")
                    if os.path.exists(lang_source):
                        print(f"Updating language folder...")
                        try:
                            if os.path.exists(lang_target):
                                shutil.rmtree(lang_target)
                            shutil.copytree(lang_source, lang_target)
                            print(f"✓ Language files updated")
                        except Exception as e:
                            print(f"Warning: Could not update language files: {e}")
                    
                    # Copy updater.exe if exists and not self
                    updater_source = os.path.join(temp_dir, "updater.exe")
                    if os.path.exists(updater_source):
                        updater_target = os.path.join(target_dir, "updater.exe")
                        current_updater = os.path.abspath(sys.executable)
                        
                        # Don't try to update self
                        if os.path.abspath(updater_target) != current_updater:
                            print(f"Updating updater.exe...")
                            try:
                                if os.path.exists(updater_target):
                                    os.remove(updater_target)
                                shutil.copy2(updater_source, updater_target)
                                print(f"✓ Updater updated")
                            except Exception as e:
                                print(f"Warning: Could not update updater: {e}")
                        else:
                            print(f"Skipping updater.exe (currently running)")
                    
                    # Copy other files at root level (excluding config)
                    print(f"Copying additional files...")
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        target_path = os.path.join(target_dir, item)
                        
                        # Skip executable, updater, language folder, temp dirs, and config files
                        if (item.endswith('.exe') or 
                            item == "language" or 
                            item.endswith('.json') or
                            item == "update_temp" or
                            item.startswith('.')):
                            continue
                        
                        try:
                            if os.path.isfile(item_path):
                                print(f"  Copying {item}...")
                                shutil.copy2(item_path, target_path)
                            elif os.path.isdir(item_path):
                                print(f"  Copying directory {item}...")
                                if os.path.exists(target_path):
                                    shutil.rmtree(target_path)
                                shutil.copytree(item_path, target_path)
                        except Exception as e:
                            print(f"  Warning: Could not copy {item}: {e}")
                    
                    break
            
            if exe_found:
                break
        
        if not exe_found:
            print(f"\n✗ ERROR: Could not find portable executable")
            print(f"Expected: {exe_name}")
            print(f"Searched in: {temp_dir}")
            raise Exception(f"Portable executable not found in update package")
        
        # Clean up
        print("\n=== Cleaning up ===")
        print("Removing temp directory...")
        shutil.rmtree(temp_dir)
        print("Removing update file...")
        os.remove(zip_file)
        print("✓ Cleanup complete")
        
        # Restart application
        print("\n=== Restarting application ===")
        print("Waiting 1 second...")
        time.sleep(1)
        exe_path = os.path.join(target_dir, exe_name)
        print(f"Starting: {exe_path}")
        subprocess.Popen([exe_path], cwd=target_dir)
        print("✓ Application started")
        
    except Exception as e:
        # Try to restore backup on failure
        print(f"\n✗ ERROR: {e}")
        backup_file = os.path.join(target_dir, exe_name + ".backup")
        target_file = os.path.join(target_dir, exe_name)
        
        if os.path.exists(backup_file):
            print("Restoring backup due to error...")
            try:
                shutil.copy2(backup_file, target_file)
                print("✓ Backup restored")
            except Exception as restore_error:
                print(f"✗ Could not restore backup: {restore_error}")
        
        raise e

def install_setup_update(setup_file):
    """Install setup version"""
    print(f"Running installer: {setup_file}")
    
    # Run installer with silent flags
    result = subprocess.run(
        [setup_file, '/VERYSILENT', '/NORESTART', '/SUPPRESSMSGBOXES'],
        capture_output=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Installer failed with code {result.returncode}")
    
    # Clean up installer
    print("Cleaning up...")
    time.sleep(2)
    try:
        os.remove(setup_file)
    except:
        pass
    
    print("Installation completed. Please restart the application manually.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nUpdate cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)