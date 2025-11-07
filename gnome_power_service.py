#!/usr/bin/env python3

import argparse
from datetime import datetime
import json
import logging
import os
import psutil
import subprocess
import re
import time
import glob

# if needed
# sudo apt install python3-pydbus
# sudo apt install libdbus-1-dev libdbus-glib-1-dev

ver = '0.2'
# Setup logging
log_file = os.path.expanduser('~/gnome-power-service.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

CONFIG_DIR = os.path.expanduser("~/.config/gnome_power_service")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CACHE_FILE = os.path.expanduser("~/.cache/brightness_check.json")

def load_config():
    default_config = {
        "dim_screen": True,
        "change_theme": False,
        "light_theme": "Yaru",
        "dark_theme": "Yaru-dark",
        "keyboard_brightness": [25, 65]
    }
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    # Update with missing defaults
    updated = False
    for key, value in default_config.items():
        if key not in config:
            config[key] = value
            updated = True
    if updated:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    return config

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_power_status():
    battery = psutil.sensors_battery()
    if battery is None:
        return "Battery information not available"
    elif battery.power_plugged:
        return "AC"
    else:
        return "Battery"


def set_keyboard_brightness(percent: int):
    """
    Set GNOME display brightness (GNOME 49 compatible)
    via org.gnome.SettingsDaemon.Power.Keyboard
    """
    if not 0 <= percent <= 100:
        raise ValueError("Brightness must be between 0 and 100")

    bus = SessionBus()
    try:
        obj = bus.get("org.gnome.SettingsDaemon.Power", "/org/gnome/SettingsDaemon/Power")
        iface = obj["org.gnome.SettingsDaemon.Power.Keyboard"]
        iface.Brightness = percent
    except Exception as e:
        print(f"Error setting keyboard brightness: {e}")


#!/usr/bin/env python3
from pydbus import SessionBus

BUS_NAME = "org.gnome.Shell"
OBJ_PATH = "/org/gnome/Shell/Brightness"
IFACE = "org.gnome.Shell.Brightness"

bus = SessionBus()
brightness = bus.get(BUS_NAME, OBJ_PATH)

def has_brightness_control():
    """Return True if brightness control is available."""
    return brightness.Get(IFACE, "HasBrightnessControl")

def set_dimming(enable: bool):
    """Enable or disable dimming."""
    brightness.SetDimming(enable)


def set_power_profile(profile: str):
    """
    Set the system power profile.
    profile must be one of: 'power-saver', 'balanced', 'performance'
    """
    if profile not in ('power-saver', 'balanced', 'performance'):
        raise ValueError("Invalid profile name")
    subprocess.run(['powerprofilesctl', 'set', profile], check=True)


def set_theme(theme_name: str):
    """Set the GTK theme and color scheme."""
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'gtk-theme', theme_name], check=True)
    if theme_name.endswith('-dark'):
        color_scheme = 'prefer-dark'
    else:
        color_scheme = 'default'
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'color-scheme', color_scheme], check=True)
    logging.info(f"Theme set to {theme_name} with color scheme {color_scheme}")

def install_service():
    script_path = os.path.abspath(__file__)
    home_dir = os.path.expanduser("~")
    bin_dir = os.path.join(home_dir, ".local", "bin")

    # Check if script is not in ~/.local/bin, copy it there
    if not script_path.startswith(bin_dir):
        os.makedirs(bin_dir, exist_ok=True)
        new_script_path = os.path.join(bin_dir, "gnome_power_service.py")

        # Copy the script to ~/.local/bin
        import shutil
        shutil.copy2(script_path, new_script_path)
        os.chmod(new_script_path, 0o755)  # Make executable
        script_path = new_script_path
        logging.info(f"Script copied to {script_path}")

    service_content = f"""[Unit]
Description=GNOME Power Service
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {script_path}
"""
    timer_content = """[Unit]
Description=GNOME Power Service Timer
Requires=gnome-power-service.service

[Timer]
OnActiveSec=0
OnUnitActiveSec=60
AccuracySec=1s

[Install]
WantedBy=timers.target
"""
    service_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(service_dir, exist_ok=True)
    service_file = os.path.join(service_dir, "gnome-power-service.service")
    timer_file = os.path.join(service_dir, "gnome-power-service.timer")
    with open(service_file, 'w') as f:
        f.write(service_content)
    with open(timer_file, 'w') as f:
        f.write(timer_content)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', 'gnome-power-service.timer'], check=True)
    subprocess.run(['systemctl', '--user', 'start', 'gnome-power-service.timer'], check=True)
    logging.info("Service and timer installed and started.")

def uninstall_service():
    subprocess.run(['systemctl', '--user', 'stop', 'gnome-power-service.timer'], check=False)
    subprocess.run(['systemctl', '--user', 'disable', 'gnome-power-service.timer'], check=False)
    subprocess.run(['systemctl', '--user', 'stop', 'gnome-power-service.service'], check=False)
    service_dir = os.path.expanduser("~/.config/systemd/user")
    service_file = os.path.join(service_dir, "gnome-power-service.service")
    timer_file = os.path.join(service_dir, "gnome-power-service.timer")
    if os.path.exists(service_file):
        os.remove(service_file)
    if os.path.exists(timer_file):
        os.remove(timer_file)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    logging.info("Service and timer uninstalled.")

def service_status():
    result_timer = subprocess.run(['systemctl', '--user', 'is-active', 'gnome-power-service.timer'], capture_output=True, text=True)
    result_service = subprocess.run(['systemctl', '--user', 'is-active', 'gnome-power-service.service'], capture_output=True, text=True)
    if result_timer.returncode == 0:
        logging.info("Timer is active.")
    else:
        logging.info("Timer is inactive.")
    if result_service.returncode == 0:
        logging.info("Service is currently running.")
    else:
        logging.info("Service is not running.")

def config_service():
    editor = os.environ.get('EDITOR', 'nano')
    subprocess.run([editor, CONFIG_FILE])

def reload_service():
    subprocess.run(['systemctl', '--user', 'restart', 'gnome-power-service.timer'], check=True)
    logging.info("Service reloaded.")

def get_screen_status():
    """
    Query GNOME Mutter DisplayConfig.PowerSaveMode via gdbus.
    Returns one of: 'on', 'dimmed', 'blanked', 'off', or 'unknown'.
    """
    try:
        result = subprocess.run([
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Mutter.DisplayConfig",
            "--object-path", "/org/gnome/Mutter/DisplayConfig",
            "--method", "org.freedesktop.DBus.Properties.Get",
            "org.gnome.Mutter.DisplayConfig", "PowerSaveMode"
        ], capture_output=True, text=True, check=True)

        stdout = result.stdout.strip()  # e.g. '(<0>,)'
        # primary pattern: matches '(<0>,)', '(<0>, )', '(< 0 >,)' etc.
        m = re.search(r'<\s*(\d+)\s*>', stdout)

        if not m:
            return "unknown"

        mode = int(m.group(1))
        return {0: "on", 1: "dimmed", 2: "blanked", 3: "off"}.get(mode, "unknown")

    except subprocess.CalledProcessError:
        return "unknown"

def get_actual_brightness():
    """Return current actual backlight brightness value"""
    paths = glob.glob("/sys/class/backlight/*/actual_brightness")
    if not paths:
        return None
    try:
        with open(paths[0]) as f:
            return int(f.read().strip())
    except Exception:
        return None


def get_gnome_idle_time():
    """Return GNOME idle time in seconds (Wayland-safe)."""
    try:
        result = subprocess.run(
            [
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Mutter.IdleMonitor",
                "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
                "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"
            ],
            capture_output=True, text=True, timeout=2
        )
        m = re.search(r"\(uint64 (\d+),\)", result.stdout)
        if m:
            return int(m.group(1)) / 1000.0  # ms → s
    except Exception:
        pass
    return 0.0


def get_last_cached_value():
    """Load cached brightness and timestamp if exists."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_current_state(brightness):
    """Save current brightness and timestamp."""
    data = {"brightness": brightness, "timestamp": time.time()}
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)


def detect_auto_dim():
    """Return True if screen appears dimmed automatically."""
    current_brightness = get_actual_brightness()
    prev = get_last_cached_value()
    idle_time = get_gnome_idle_time()

    # Save current brightness for next comparison
    save_current_state(current_brightness)

    # First run, nothing to compare
    if not prev:
        return False

    prev_brightness = prev["brightness"]

    # Detect dimming when system idle and brightness lowered
    if idle_time > 1 and current_brightness < prev_brightness:
        return True

    return False

if __name__ == "__main__":

    config = load_config()

    parser = argparse.ArgumentParser(description='GNOME Power Service')
    parser.add_argument('--install', action='store_true', help='Install the service')
    parser.add_argument('--uninstall', action='store_true', help='Uninstall the service')
    parser.add_argument('--status', action='store_true', help='Check service status')
    parser.add_argument('--config', action='store_true', help='Edit configuration file')
    parser.add_argument('--reload', action='store_true', help='Reload the service')
    parser.add_argument('--version', action='store_true', help='Show version')

    args = parser.parse_args()

    if args.install:
        install_service()
    elif args.uninstall:
        uninstall_service()
    elif args.status:
        service_status()
    elif args.config:
        config_service()
    elif args.reload:
        reload_service()
    elif args.version:
        print('Version: {ver}')
    else:
        # Default behavior: run the power management logic
        if has_brightness_control():
            power_status = get_power_status()
            logging.info(f"Power mode: {power_status}")
            screen = get_screen_status()
            logging.info(f'Screen: {screen}')
            dimmed = detect_auto_dim()
            logging.info(f'Dimmed: {dimmed}')
            if power_status == 'Battery':
                logging.info('Power-saver mode')
                set_power_profile('power-saver')
                if screen == 'on' and not dimmed:
                    kb_brightness = config['keyboard_brightness'][0]
                    logging.info(f'Keyboard brightness: {kb_brightness}')
                    set_keyboard_brightness(kb_brightness)
                    if config['dim_screen']:
                        logging.info("Enabling dimming")
                        set_dimming(True)
                    if config['change_theme']:
                        set_theme(config['dark_theme'])
                elif screen == 'off':
                    kb_brightness = 0
                    logging.info(f'Keyboard brightness: {kb_brightness}')
                    set_keyboard_brightness(kb_brightness)
            elif power_status == 'AC':
                logging.info('Balanced mode')
                set_power_profile('balanced')
                if screen == 'on' and not dimmed:
                    kb_brightness = config['keyboard_brightness'][1]
                    logging.info(f'Keyboard brightness: {kb_brightness}')
                    set_keyboard_brightness(kb_brightness)
                    if config['dim_screen']:
                        logging.info("Disable dimming")
                        set_dimming(False)
                    if config['change_theme']:
                        set_theme(config['light_theme'])
                elif screen == 'off':
                    kb_brightness = 0
                    logging.info(f'Keyboard brightness: {kb_brightness}')
                    set_keyboard_brightness(kb_brightness)

            else:
                logging.info("Unknown power status")
        else:
            logging.info("No brightness control")
