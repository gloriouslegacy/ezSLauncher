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
    extract_dir = os.path.join(os.path.dirname(zip_file), "extracted")
    
    try:
        # Extract zip to temp directory
        print("Extracting update...")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        print(f"✓ Extraction complete")
        
        # Find the executable in extracted files
        # Priority: 1) Exact match, 2) Any .exe with 'Portable' in name, 3) First .exe found
        new_exe = None
        found_exe_name = None
        
        # First pass: Look for exact match or Portable exe
        for item in os.listdir(extract_dir):
            if item == exe_name:
                new_exe = os.path.join(extract_dir, item)
                found_exe_name = item
                print(f"✓ Found exact match: {item}")
                break
            elif item.endswith('.exe') and 'Portable' in item:
                new_exe = os.path.join(extract_dir, item)
                found_exe_name = item
                print(f"✓ Found portable exe: {item}")
                break
        
        # Second pass: If no portable exe found, take first .exe
        if not new_exe:
            for item in os.listdir(extract_dir):
                if item.endswith('.exe') and item != 'updater.exe':
                    new_exe = os.path.join(extract_dir, item)
                    found_exe_name = item
                    print(f"✓ Found exe: {item}")
                    break
        
        if not new_exe or not os.path.exists(new_exe):
            raise Exception(f"Could not find any executable in update package")
        
        # Backup current executable
        target_file = os.path.join(target_dir, exe_name)
        backup_file = target_file + ".backup"
        
        print("Creating backup...")
        if os.path.exists(target_file):
            if os.path.exists(backup_file):
                os.remove(backup_file)
            shutil.copy2(target_file, backup_file)
            print(f"✓ Backup created")
        
        # Replace executable
        print(f"Replacing {exe_name}...")
        if os.path.exists(target_file):
            os.remove(target_file)
        shutil.copy2(new_exe, target_file)
        print(f"✓ Successfully replaced executable")
        
        # Copy language folder if exists
        lang_source = os.path.join(extract_dir, "language")
        lang_target = os.path.join(target_dir, "language")
        if os.path.exists(lang_source):
            print("Updating language folder...")
            if os.path.exists(lang_target):
                shutil.rmtree(lang_target)
            shutil.copytree(lang_source, lang_target)
            print(f"✓ Language files updated")
        
        # Copy updater.exe if exists and not self
        updater_source = os.path.join(extract_dir, "updater.exe")
        if os.path.exists(updater_source):
            updater_target = os.path.join(target_dir, "updater.exe")
            current_updater = os.path.abspath(sys.executable)
            
            # Don't try to update self
            if os.path.abspath(updater_target) != current_updater:
                print("Updating updater.exe...")
                if os.path.exists(updater_target):
                    os.remove(updater_target)
                shutil.copy2(updater_source, updater_target)
                print(f"✓ Updater updated")
            else:
                print("Skipping updater.exe (currently running)")
        
        # Clean up
        print("\n=== Cleaning up ===")
        print("Removing temp directory...")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        print("Removing update file...")
        if os.path.exists(zip_file):
            os.remove(zip_file)
        print("✓ Cleanup complete")
        
        # Restart application
        print("\n=== Restarting application ===")
        print("Waiting 2 seconds...")
        time.sleep(2)
        exe_path = os.path.join(target_dir, exe_name)
        print(f"Starting: {exe_path}")
        subprocess.Popen([exe_path], cwd=target_dir, shell=False)
        print("✓ Application started")
        
    except Exception as e:
        # Try to restore backup on failure
        print(f"\n✗ ERROR: {e}")
        backup_file = os.path.join(target_dir, exe_name + ".backup")
        target_file = os.path.join(target_dir, exe_name)
        
        if os.path.exists(backup_file):
            print("Restoring backup due to error...")
            try:
                if os.path.exists(target_file):
                    os.remove(target_file)
                shutil.copy2(backup_file, target_file)
                print("✓ Backup restored")
                # Restart original version
                subprocess.Popen([target_file], cwd=target_dir, shell=False)
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