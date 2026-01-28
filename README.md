# GNOME Power Service

A Python service that automatically adjusts GNOME power settings based on whether your laptop is plugged in or running on battery power.

## Features

- **Power Profile Management**: Automatically switches between power-saver (battery) and balanced (AC) modes
- **Keyboard Brightness Control**: Adjusts keyboard backlight brightness based on power source
- **Screen Dimming**: Enables dimming on battery to save power
- **Theme Switching**: Optionally switches between light and dark GTK themes
- **Systemd Integration**: Runs as a user service with automatic timer-based execution

## Tested

- Ubuntu 25.10

## Requirements

- GNOME Desktop Environment
- Python 3.6+
- `psutil` and `pydbus` Python packages
- `powerprofilesctl` (usually available on modern Linux distributions)

## Installation

1. Install Python dependencies:
   ```bash
   pip install psutil pydbus
   ```

2. Install system dependencies (Ubuntu/Debian):
   ```bash
   sudo apt install python3-pydbus libdbus-1-dev libdbus-glib-1-dev
   ```
   #### 2.1 For brightness control
   ```bash
   sudo apt install brightnessctl
   ```

3. Install the service:
   ```bash
   python3 gnome_power_service.py --install
   ```

This will:
- Create systemd user service and timer files
- Enable and start the timer (runs every 30 seconds)

## Usage

The service runs automatically in the background. You can also run it manually:

```bash
python3 gnome_power_service.py
```

### Command Line Options

- `--install`: Install the service and timer
- `--uninstall`: Remove the service and timer
- `--status`: Check if the service is running
- `--config`: Edit the configuration file
- `--reload`: Restart the service

## Configuration

Edit the configuration file at `~/.config/gnome_power_service/config.json`:

```json
{
    "dim_screen": true,
    "change_theme": false,
    "light_theme": "Yaru",
    "dark_theme": "Yaru-dark",
    "keyboard_brightness": [25, 65]
}
```

- `dim_screen`: Enable/disable automatic screen dimming on battery
- `change_theme`: Enable/disable automatic theme switching
- `light_theme`: GTK theme name for AC power
- `dark_theme`: GTK theme name for battery power
- `keyboard_brightness`: Array of [battery_percent, ac_percent] for keyboard brightness

## Uninstallation

To remove the service:

```bash
python3 gnome_power_service.py --uninstall
```

This stops and disables the timer, removes service files, and reloads systemd.

## Logging

Logs are written to `~/gnome-power-service.log` with timestamps and include:
- Power status changes
- Profile switches
- Brightness adjustments
- Theme changes

## Troubleshooting

- Ensure `powerprofilesctl` is available
- Check systemd user services: `systemctl --user status gnome-power-service.timer`
- Verify GNOME Settings Daemon is running
- Check logs in `~/gnome-power-service.log`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.