# Power Service Settings (separate app)

GNOME-style (GTK4 + libadwaita) settings GUI for GNOME Power Service.
Lives in its own folder so it can evolve independently of the service script.

## Run

```bash
python3 app.py
```

## Install system deps (Ubuntu/Debian)

```bash
sudo apt install gir1.2-gtk-4.0 gir1.2-adw-1 python3-gi
```

## Optional: app launcher

```bash
cp gnome-power-settings.desktop ~/.local/share/applications/
```

## What it does

- Edits the same config file as the service:
  `~/.config/gnome_power_service/config.json`
- Changes apply instantly (no Save button needed)
- Shows systemd timer status and offers Install / Reload / Uninstall
  by calling `gnome_power_service.py` with `--install`, `--reload`,
  `--uninstall`.
