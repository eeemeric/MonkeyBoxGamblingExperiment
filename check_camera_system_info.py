def check_camera_system_info(self):
    """Check and display camera system information"""
    import subprocess
    import os
    
    print("=== Camera System Information ===")
    
    # Check Pi OS version
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = f.read()
            if 'bookworm' in os_info.lower():
                print("Detected: Raspberry Pi OS Bookworm")
            elif 'bullseye' in os_info.lower():
                print("Detected: Raspberry Pi OS Bullseye")
            else:
                print("Detected: Other Raspberry Pi OS version")
    except:
        print("Could not detect Pi OS version")
    
    # Check available camera commands
    camera_commands = ['rpicam-hello', 'rpicam-still', 'rpicam-vid', 
                    'libcamera-hello', 'libcamera-still', 'libcamera-vid']
    
    print("\nAvailable camera commands:")
    for cmd in camera_commands:
        try:
            result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                print(f"  ✓ {cmd}: {result.stdout.strip()}")
            else:
                print(f"  ✗ {cmd}: Not found")
        except:
            print(f"  ✗ {cmd}: Error checking")
    
    # Check camera detection
    print("\nCamera detection:")
    try:
        result = subprocess.run(['rpicam-hello', '--list-cameras'], 
                            capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("rpicam-hello output:")
            print(result.stdout)
        else:
            print("rpicam-hello failed, trying libcamera-hello...")
            result = subprocess.run(['libcamera-hello', '--list-cameras'], 
                                capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("libcamera-hello output:")
                print(result.stdout)
    except Exception as e:
        print(f"Camera detection failed: {e}")
    
    # Check config files
    config_files = ['/boot/config.txt', '/boot/firmware/config.txt']
    print("\nCamera configuration:")
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    if 'camera' in content.lower():
                        print(f"Found camera settings in {config_file}")
                        for line in content.split('\n'):
                            if 'camera' in line.lower() and not line.strip().startswith('#'):
                                print(f"  {line.strip()}")
            except:
                print(f"Could not read {config_file}")