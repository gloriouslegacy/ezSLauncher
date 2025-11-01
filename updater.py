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
        
        # Find the executable in extracted files
        exe_found = False
        for root, dirs, files in os.walk(temp_dir):
            if exe_name in files:
                source_file = os.path.join(root, exe_name)
                target_file = os.path.join(target_dir, exe_name)
                
                # Backup old executable
                backup_file = target_file + ".backup"
                if os.path.exists(target_file):
                    print(f"Creating backup: {backup_file}")
                    shutil.copy2(target_file, backup_file)
                
                # Replace executable
                print(f"Replacing {exe_name}...")
                shutil.copy2(source_file, target_file)
                exe_found = True
                
                # Copy language folder if exists
                lang_source = os.path.join(root, "language")
                lang_target = os.path.join(target_dir, "language")
                if os.path.exists(lang_source):
                    print("Updating language files...")
                    if os.path.exists(lang_target):
                        shutil.rmtree(lang_target)
                    shutil.copytree(lang_source, lang_target)
                
                # Copy other files (excluding config)
                for item in os.listdir(root):
                    item_path = os.path.join(root, item)
                    target_path = os.path.join(target_dir, item)
                    
                    # Skip executable (already copied), language folder, and config files
                    if item == exe_name or item == "language" or item.endswith('.json'):
                        continue
                    
                    if os.path.isfile(item_path):
                        print(f"Copying {item}...")
                        shutil.copy2(item_path, target_path)
                    elif os.path.isdir(item_path):
                        if os.path.exists(target_path):
                            shutil.rmtree(target_path)
                        shutil.copytree(item_path, target_path)
                
                break
        
        if not exe_found:
            raise Exception(f"Executable {exe_name} not found in update package")
        
        # Clean up
        print("Cleaning up...")
        shutil.rmtree(temp_dir)
        os.remove(zip_file)
        
        # Restart application
        print("Restarting application...")
        time.sleep(1)
        exe_path = os.path.join(target_dir, exe_name)
        subprocess.Popen([exe_path], cwd=target_dir)
        
    except Exception as e:
        # Try to restore backup on failure
        backup_file = os.path.join(target_dir, exe_name + ".backup")
        target_file = os.path.join(target_dir, exe_name)
        
        if os.path.exists(backup_file):
            print("Restoring backup due to error...")
            shutil.copy2(backup_file, target_file)
        
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
