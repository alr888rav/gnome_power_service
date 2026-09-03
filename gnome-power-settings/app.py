#!/usr/bin/env python3
"""GNOME-style settings app for GNOME Power Service.

Run with: python3 app.py
Requires: GTK4 + libadwaita (gir1.2-gtk-4.0, gir1.2-adw-1), PyGObject
"""

import json
import os
import subprocess
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

CONFIG_DIR = os.path.expanduser("~/.config/gnome_power_service")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "dim_screen": False,
    "change_theme": False,
    "light_theme": "Yaru",
    "dark_theme": "Yaru-dark",
    "keyboard_control": True,
    "keyboard_brightness": [25, 65],
    "brightness_control": True,
    "screen_brightness": [25, 55],
    "power_control": True,
    "cpu_turbo_control": True,
}


def find_service_script() -> str:
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "gnome_power_service.py"),
        os.path.expanduser("~/my/gnome_power_service.py"),
        "/usr/local/bin/gnome_power_service.py",
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    return os.path.abspath(candidates[0])


SERVICE_SCRIPT = find_service_script()


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)
    updated = False
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
            updated = True
    for key in ("keyboard_brightness", "screen_brightness"):
        val = config.get(key)
        if (not isinstance(val, list) or len(val) != 2
                or not all(isinstance(v, (int, float)) for v in val)):
            config[key] = list(DEFAULT_CONFIG[key])
            updated = True
    if updated:
        save_config(config)
    return config


def save_config(config: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def service_state(unit: str) -> str:
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run_service_action(*args: str) -> tuple:
    try:
        r = subprocess.run(
            [sys.executable, SERVICE_SCRIPT, *args],
            capture_output=True, text=True, timeout=60,
        )
        msg = (r.stdout.strip() or r.stderr.strip() or "Done").splitlines()[-1]
        return r.returncode == 0, msg
    except Exception as e:  # noqa: BLE001
        return False, str(e)


class SettingsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Power Service Settings")
        self.set_default_size(560, 680)

        self.config = load_config()

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        toolbar_view = Adw.ToolbarView()
        self.toast_overlay.set_child(toolbar_view)

        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle.new(
            "Power Service", "GNOME Power Service Settings"))
        toolbar_view.add_top_bar(header)

        page = Adw.PreferencesPage()
        toolbar_view.set_content(page)

        page.add(self._power_group())
        page.add(self._display_group())
        page.add(self._keyboard_group())
        page.add(self._appearance_group())
        page.add(self._service_group())

        self._refresh_service_status()
        self._update_sensitivities()

    # -- helpers ------------------------------------------------------
    def _toast(self, message: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast.new(message))

    def _persist(self) -> None:
        save_config(self.config)

    def _make_switch(self, title: str, subtitle: str, key: str) -> Adw.SwitchRow:
        row = Adw.SwitchRow.new()
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_active(bool(self.config.get(key, DEFAULT_CONFIG[key])))
        row.connect("notify::active", self._on_switch, key)
        return row

    def _on_switch(self, row: Adw.SwitchRow, _pspec, key: str) -> None:
        self.config[key] = row.get_active()
        self._persist()
        self._update_sensitivities()

    def _make_brightness_spin(self, title: str, pair_key: str, index: int,
                              subtitle: str) -> Adw.SpinRow:
        adjustment = Gtk.Adjustment.new(
            self.config[pair_key][index], 0, 100, 1, 10, 0)
        row = Adw.SpinRow.new_with_range(0, 100, 1)
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_adjustment(adjustment)
        row.set_numeric(True)
        row.connect("notify::value", self._on_spin, pair_key, index)
        return row

    def _on_spin(self, row: Adw.SpinRow, _pspec, pair_key: str, index: int) -> None:
        pair = list(self.config[pair_key])
        pair[index] = int(row.get_value())
        self.config[pair_key] = pair
        self._persist()

    # -- groups -------------------------------------------------------
    def _power_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup.new()
        group.set_title("Power")
        group.set_description("Power profile and CPU behaviour")
        group.add(self._make_switch(
            "Manage power profile",
            "Switch between power-saver on battery and balanced on AC",
            "power_control"))
        group.add(self._make_switch(
            "Manage CPU turbo boost",
            "Disable turbo on battery, enable on AC",
            "cpu_turbo_control"))
        return group

    def _display_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup.new()
        group.set_title("Display")
        group.set_description("Screen brightness and dimming")
        self.brightness_switch = self._make_switch(
            "Manage screen brightness",
            "Lower brightness on battery, raise on AC",
            "brightness_control")
        group.add(self.brightness_switch)
        self.screen_battery_row = self._make_brightness_spin(
            "On battery", "screen_brightness", 0,
            "Brightness level when unplugged")
        self.screen_ac_row = self._make_brightness_spin(
            "Plugged in", "screen_brightness", 1,
            "Brightness level when on AC power")
        group.add(self.screen_battery_row)
        group.add(self.screen_ac_row)
        group.add(self._make_switch(
            "Dim screen on battery",
            "Enable GNOME dimming when unplugged",
            "dim_screen"))
        return group

    def _keyboard_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup.new()
        group.set_title("Keyboard")
        group.set_description("Keyboard backlight brightness")
        self.keyboard_switch = self._make_switch(
            "Manage keyboard backlight",
            "Adjust keyboard brightness by power source",
            "keyboard_control")
        group.add(self.keyboard_switch)
        self.kb_battery_row = self._make_brightness_spin(
            "On battery", "keyboard_brightness", 0,
            "Backlight level when unplugged")
        self.kb_ac_row = self._make_brightness_spin(
            "Plugged in", "keyboard_brightness", 1,
            "Backlight level when on AC power")
        group.add(self.kb_battery_row)
        group.add(self.kb_ac_row)
        return group

    def _appearance_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup.new()
        group.set_title("Appearance")
        group.set_description("Automatic theme switching")
        self.theme_switch = self._make_switch(
            "Switch theme by power source",
            "Use light theme on AC, dark theme on battery",
            "change_theme")
        group.add(self.theme_switch)
        self.light_theme_row = Adw.EntryRow.new()
        self.light_theme_row.set_title("Light theme (AC)")
        self.light_theme_row.set_text(str(self.config.get("light_theme", "")))
        self.light_theme_row.connect("notify::text", self._on_theme_text,
                                     "light_theme")
        group.add(self.light_theme_row)
        self.dark_theme_row = Adw.EntryRow.new()
        self.dark_theme_row.set_title("Dark theme (battery)")
        self.dark_theme_row.set_text(str(self.config.get("dark_theme", "")))
        self.dark_theme_row.connect("notify::text", self._on_theme_text,
                                    "dark_theme")
        group.add(self.dark_theme_row)
        return group

    def _on_theme_text(self, row: Adw.EntryRow, _pspec, key: str) -> None:
        text = row.get_text().strip()
        if text:
            self.config[key] = text
            self._persist()

    def _service_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup.new()
        group.set_title("Background service")
        group.set_description("systemd user timer, runs every 30 seconds")
        self.status_row = Adw.ActionRow.new()
        self.status_row.set_title("Service status")
        group.add(self.status_row)

        btn_row = Adw.ActionRow.new()
        btn_row.set_title("Timer control")
        btn_row.set_subtitle("Install, reload or remove the systemd timer")
        box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        box.set_valign(Gtk.Align.CENTER)
        install_btn = Gtk.Button.new_with_label("Install")
        install_btn.add_css_class("suggested-action")
        install_btn.connect("clicked", self._on_service_btn, "--install",
                            "Service installed")
        box.append(install_btn)
        reload_btn = Gtk.Button.new_with_label("Reload")
        reload_btn.connect("clicked", self._on_service_btn, "--reload",
                           "Service reloaded")
        box.append(reload_btn)
        uninstall_btn = Gtk.Button.new_with_label("Uninstall")
        uninstall_btn.add_css_class("destructive-action")
        uninstall_btn.connect("clicked", self._on_service_btn, "--uninstall",
                              "Service uninstalled")
        box.append(uninstall_btn)
        btn_row.add_suffix(box)
        group.add(btn_row)
        return group

    def _on_service_btn(self, _btn: Gtk.Button, action: str, ok_msg: str) -> None:
        ok, msg = run_service_action(action)
        self._toast(ok_msg if ok else "Failed: %s" % msg)
        self._refresh_service_status()

    def _refresh_service_status(self) -> None:
        timer = service_state("gnome-power-service.timer")
        self.status_row.set_subtitle("Timer: %s" % timer)

    def _update_sensitivities(self) -> None:
        for row in (self.screen_battery_row, self.screen_ac_row):
            row.set_sensitive(bool(self.config.get("brightness_control")))
        for row in (self.kb_battery_row, self.kb_ac_row):
            row.set_sensitive(bool(self.config.get("keyboard_control")))
        theme_on = bool(self.config.get("change_theme"))
        self.light_theme_row.set_sensitive(theme_on)
        self.dark_theme_row.set_sensitive(theme_on)


class SettingsApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.example.GnomePowerService",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SettingsWindow(self)
        win.present()


def main() -> int:
    app = SettingsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
