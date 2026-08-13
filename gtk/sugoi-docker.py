#!/usr/bin/env python3
import os
import shlex
import subprocess
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio, Pango, Gdk, GdkPixbuf

__version__ = "1.0.0"

CMD = "sugoi-docker-cli"

DATA_DIRS = [
    "/usr/share/sugoi-docker",
]

ACCENT_LIGHT = "#3584e4"
ACCENT_DARK = "#62a0ea"

STUDIO_NAME = "VANTASEED"
GITHUB_URL = "https://github.com/VANTASEED"

TAGLINE = (
    "Powered by copious amounts of instant noodles, questionable caffeine "
    "tolerance,\nand a stubborn refusal to go touch grass."
)

PRIVILEGED = {"start", "stop", "restart", "enable", "disable", "prune", "prunevol"}

DARK_PALETTE = {
    0: "#000000", 1: "#cc0000", 2: "#00cc00", 3: "#cccc00",
    4: "#0000ee", 5: "#cc00cc", 6: "#00cccc", 7: "#d6d6d6",
    8: "#7f7f7f", 9: "#ff0000", 10: "#00ff00", 11: "#ffff00",
    12: "#5c5cff", 13: "#ff00ff", 14: "#00ffff", 15: "#ffffff",
}

LIGHT_PALETTE = {
    0: "#404040", 1: "#b00000", 2: "#008000", 3: "#9a6a00",
    4: "#0000c8", 5: "#a000a0", 6: "#008080", 7: "#909090",
    8: "#6a6a6a", 9: "#d00000", 10: "#00a000", 11: "#b8860b",
    12: "#0000ff", 13: "#d000d0", 14: "#00b0b0", 15: "#1a1a1a",
}


def _xterm_256():
    pal = {}
    cube = [0, 95, 135, 175, 215, 255]
    for n in range(216):
        r = cube[n // 36]
        g = cube[(n // 6) % 6]
        b = cube[n % 6]
        pal[16 + n] = f"#{r:02x}{g:02x}{b:02x}"
    for n in range(24):
        v = 8 + n * 10
        pal[232 + n] = f"#{v:02x}{v:02x}{v:02x}"
    return pal


_XTERM_256 = _xterm_256()


class DockerCtlGUI(Gtk.Application):
    SPINNER = "\u280b\u2819\u2818\u283c\u2834\u2826\u2827\u2807\u280f"

    def __init__(self):
        super().__init__(application_id="dev.sugoi.docker")
        self.win = None
        self.dark = False
        self._tags = {}
        self.log_entry = None
        self._buttons = []
        self._spinner_id = 0
        self._spinner_idx = 0
        self._busy = False

    def do_activate(self):
        if self.win is not None:
            self.win.present()
            return
        self.apply_theme()
        self.monitor_theme()
        self._apply_css()
        self.build_ui()
        self.win.show_all()
        self.refresh_status()

    def _apply_css(self):
        css = b"""
paned separator,
paned > separator {
    background-color: transparent;
    background-image: none;
    border: none;
    box-shadow: none;
}

button.start-btn {
    background-image: linear-gradient(
        to bottom,
        shade(@theme_selected_bg_color, 1.12),
        shade(@theme_selected_bg_color, 0.92)
    );
    border: 1px solid shade(@theme_selected_bg_color, 0.72);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.28);
    color: @theme_selected_fg_color;
}
button.start-btn:hover {
    background-image: linear-gradient(
        to bottom,
        shade(@theme_selected_bg_color, 1.2),
        shade(@theme_selected_bg_color, 1.0)
    );
}

.text-link {
    color: alpha(@theme_fg_color, 0.55);
    background-image: none;
    background-color: transparent;
    border: none;
    box-shadow: none;
    padding: 0;
    outline: none;
}
.text-link:hover {
    color: alpha(@theme_fg_color, 0.95);
    background-image: none;
    background-color: transparent;
}
"""
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ---------------- theme ----------------
    def _system_dark(self):
        try:
            s = Gio.Settings.new("org.gnome.desktop.interface")
            scheme = s.get_string("color-scheme") or ""
            if scheme.lower() in ("prefer-dark", "dark"):
                return True
            theme = (s.get_string("gtk-theme") or "").lower()
            return "dark" in theme
        except Exception:
            pass
        try:
            theme = (Gtk.Settings.get_default().props.gtk_theme_name or "").lower()
            return "dark" in theme
        except Exception:
            return False

    def apply_theme(self):
        self.dark = self._system_dark()
        try:
            Gtk.Settings.get_default().props.gtk_application_prefer_dark_theme = self.dark
        except Exception:
            pass
        self._tags.clear()

    def monitor_theme(self):
        try:
            s = Gio.Settings.new("org.gnome.desktop.interface")
            s.connect("changed", self._on_theme_setting)
        except Exception:
            pass

    def _on_theme_setting(self, _settings, key):
        if key in ("color-scheme", "gtk-theme"):
            self.apply_theme()

    # ---------------- UI ----------------
    def build_ui(self):
        self.win = Gtk.ApplicationWindow(application=self, title="Sugoi! Docker")
        self.win.set_default_size(820, 640)

        hb = Gtk.HeaderBar(show_close_button=True)
        hb.set_title("\U0001f433 Sugoi! Docker")
        self.win.set_titlebar(hb)

        self.status_lbl = Gtk.Label(label="Checking\u2026")
        self.status_lbl.set_tooltip_text("Service running / enabled on boot")
        self.status_lbl.set_margin_start(12)
        hb.pack_start(self.status_lbl)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_border_width(10)
        self.win.add(box)

        # button list
        lb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lb.set_spacing(2)
        self._add_section(lb, "Service control")
        self._add_cmd_row(lb, "Start", "Start Docker now (won't auto-start on boot)", ["start"], privileged=True, suggested=True)
        self._add_cmd_row(lb, "Stop", "Stop Docker now", ["stop"], privileged=True)
        self._add_cmd_row(lb, "Restart", "Restart Docker now", ["restart"], privileged=True)
        self._add_cmd_row(lb, "Enable on boot", "Auto-start Docker on every boot", ["enable"], privileged=True)
        self._add_cmd_row(lb, "Disable on boot", "Cancel auto-start on boot", ["disable"], privileged=True)
        self._add_cmd_row(lb, "Status", "Show service status and boot setting", ["status"], privileged=False)

        self._add_section(lb, "Maintenance")
        self._add_cmd_row(lb, "Prune", "Remove unused containers, images, networks, build cache", ["prune"], privileged=True)
        self._add_cmd_row(lb, "Prune volumes", "Remove ALL unused volumes (deletes data)", ["prunevol"], privileged=True)

        self._add_section(lb, "Information")
        self._add_cmd_row(lb, "Info", "System-wide Docker info", ["info"], privileged=False)
        self._add_cmd_row(lb, "Version", "Docker version", ["version"], privileged=False)
        self._add_cmd_row(lb, "Images", "List downloaded images", ["images"], privileged=False)
        self._add_cmd_row(lb, "Containers", "List running containers", ["ps"], privileged=False)
        self._add_cmd_row(lb, "All containers", "List all containers (incl. stopped)", ["psall"], privileged=False)
        self._add_cmd_row(lb, "Stats", "Live resource usage (snapshot)", ["stats", "--no-stream"], privileged=False)
        self._add_log_row(lb)
        self._add_cmd_row(lb, "Refresh status", "Update the status shown in the header", None, privileged=False, refresh=True)

        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scroll.add(lb)

        # output
        self.text = Gtk.TextView()
        self.text.set_editable(False)
        self.text.set_cursor_visible(False)
        self.text.set_monospace(True)
        self.text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text.set_left_margin(10)
        self.text.set_right_margin(10)
        self.text.set_top_margin(10)
        self.text.set_bottom_margin(6)
        self._font_size = 11
        self._zoom_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider(
            self.text.get_style_context(), self._zoom_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.text.connect("scroll-event", self._on_text_scroll)
        self.text.connect("key-press-event", self._on_text_key)
        self.buf = self.text.get_buffer()
        out_scroll = Gtk.ScrolledWindow()
        out_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        out_scroll.set_margin_top(10)
        out_scroll.add(self.text)

        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        paned.pack1(list_scroll, resize=True, shrink=False)
        paned.pack2(out_scroll, resize=True, shrink=False)
        paned.set_position(360)
        box.pack_start(paned, True, True, 0)

        foot = Gtk.Label()
        foot.set_halign(Gtk.Align.END)
        foot.set_margin_top(5)
        foot.set_margin_bottom(1)
        foot.set_margin_end(10)
        foot.set_use_markup(True)
        foot.set_markup(
            f'<span foreground="#6c757d" font="10">'
            f'v{__version__} \u2022 </span>'
            f'<a href="about"><span foreground="#6c757d" font="10">About</span></a>'
        )
        foot.connect("activate-link", lambda _l, _u: self._show_about() or True)
        foot_event = Gtk.EventBox()
        foot_event.add(foot)
        foot_event.set_halign(Gtk.Align.END)
        foot_event.connect("enter-notify-event", lambda w, _e: self._hand_cursor(w, True))
        foot_event.connect("leave-notify-event", lambda w, _e: self._hand_cursor(w, False))
        box.pack_start(foot_event, False, False, 0)

    def _add_section(self, parent, title):
        lbl = Gtk.Label(xalign=0)
        lbl.set_markup(f"<b>{title}</b>")
        lbl.set_margin_top(10)
        lbl.set_margin_bottom(2)
        lbl.set_margin_start(8)
        lbl.get_style_context().add_class("dim-label")
        parent.pack_start(lbl, False, False, 0)

    def _add_cmd_row(self, parent, btn_label, desc, args, privileged, suggested=False, refresh=False):
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        h.set_margin_start(8)
        h.set_margin_end(16)
        h.set_margin_top(3)
        h.set_margin_bottom(3)

        btn = Gtk.Button(label=btn_label)
        btn.set_halign(Gtk.Align.START)
        btn.set_size_request(150, -1)
        self._buttons.append(btn)
        if suggested:
            btn.get_style_context().add_class("start-btn")

        lbl = Gtk.Label(label=desc, xalign=0)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)

        h.pack_start(btn, False, False, 0)
        h.pack_start(lbl, True, True, 0)
        parent.pack_start(h, False, False, 0)

        if refresh:
            btn.connect("clicked", lambda _b: self.refresh_status())
        else:
            btn.connect(
                "clicked",
                lambda _b, a=args, p=privileged: self._on_cmd(a, p),
            )

    def _add_log_row(self, parent):
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        h.set_margin_start(8)
        h.set_margin_end(16)
        h.set_margin_top(3)
        h.set_margin_bottom(3)

        btn = Gtk.Button(label="Show logs")
        btn.set_halign(Gtk.Align.START)
        btn.set_size_request(150, -1)
        self._buttons.append(btn)

        self.log_entry = Gtk.Entry()
        self.log_entry.set_placeholder_text("Logs for a container — enter its name or ID")
        self.log_entry.set_hexpand(True)

        h.pack_start(btn, False, False, 0)
        h.pack_start(self.log_entry, True, True, 0)
        parent.pack_start(h, False, False, 0)
        btn.connect("clicked", self._on_logs)

    # ---------------- handlers ----------------
    def _on_cmd(self, args, privileged):
        if args[0] == "prunevol" and not self._confirm(
                "Remove ALL unused volumes?",
                "This permanently deletes data from unused volumes. Continue?"):
            return
        self.run_command(args, privileged)

    def _on_logs(self, _btn):
        name = self.log_entry.get_text().strip()
        if not name:
            self._append_plain("$ sugoi-docker-cli logs <container>\nProvide a container name or ID.\n\n")
            return
        self.run_command(["logs", name], privileged=False)

    def _confirm(self, title, message):
        dlg = Gtk.MessageDialog(
            transient_for=self.win,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=title,
        )
        dlg.format_secondary_text(message)
        resp = dlg.run()
        dlg.destroy()
        return resp == Gtk.ResponseType.YES

    # ---------------- execution ----------------
    def run_command(self, args, privileged):
        self.buf.delete(self.buf.get_start_iter(), self.buf.get_end_iter())
        self._set_busy(True)
        self._start_loading()
        thread = threading.Thread(target=self._worker, args=(privileged, list(args)), daemon=True)
        thread.start()

    def _worker(self, privileged, args):
        full = (["pkexec"] if privileged else []) + [CMD] + args
        cmdline = " ".join(shlex.quote(a) for a in full)
        env = dict(os.environ)
        env.setdefault("TERM", "xterm-256color")
        env["SYSTEMD_COLORS"] = "1"
        env["CLICOLOR"] = "1"
        env["CLICOLOR_FORCE"] = "1"
        try:
            argv = ["script", "-qec", cmdline, "/dev/null"]
            proc = subprocess.run(argv, capture_output=True, text=True, env=env)
            raw = proc.stdout or proc.stderr or ""
        except Exception as exc:
            raw = f"Error: {exc}"
        raw = raw.replace("\r\n", "\n").replace("\r", "")
        GLib.idle_add(self.append_output, "$ " + " ".join(full) + "\n\n", raw)
        GLib.idle_add(self.refresh_status)

    # ---------------- output ----------------
    def append_output(self, header, body):
        self._stop_loading()
        self.buf.delete(self.buf.get_start_iter(), self.buf.get_end_iter())
        self.buf.insert(self.buf.get_end_iter(), header)
        self._append_colored(body)
        self.text.scroll_to_mark(self.buf.get_insert(), 0.0, False, 0.0, 0.0)
        self._set_busy(False)
        return False

    def _append_plain(self, text):
        self.buf.insert(self.buf.get_end_iter(), text)
        self.text.scroll_to_mark(self.buf.get_insert(), 0.0, False, 0.0, 0.0)

    # ---------------- loading / busy ----------------
    def _set_busy(self, busy):
        self._busy = busy
        for b in self._buttons:
            b.set_sensitive(not busy)
        if self.log_entry is not None:
            self.log_entry.set_sensitive(not busy)

    def _start_loading(self):
        self._spinner_idx = 0
        self._spinner_id = GLib.timeout_add(120, self._tick_loading)

    def _tick_loading(self):
        self._spinner_idx = (self._spinner_idx + 1) % len(self.SPINNER)
        buf = self.buf
        buf.delete(buf.get_start_iter(), buf.get_end_iter())
        buf.insert(buf.get_end_iter(), f"{self.SPINNER[self._spinner_idx]} Loading\u2026\n")
        return True

    def _stop_loading(self):
        if self._spinner_id:
            GLib.source_remove(self._spinner_id)
            self._spinner_id = 0

    # ---------------- text zoom ----------------
    def _on_text_scroll(self, _widget, event):
        if not (event.state & Gdk.ModifierType.CONTROL_MASK):
            return False
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            _ok, _dx, dy = event.get_scroll_deltas()
            step = 1 if dy < 0 else (-1 if dy > 0 else 0)
        else:
            step = 1 if event.direction == Gdk.ScrollDirection.UP else (
                -1 if event.direction == Gdk.ScrollDirection.DOWN else 0)
        if step:
            self._change_font_size(step)
        return True

    def _on_text_key(self, _widget, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK and event.keyval == Gdk.KEY_0:
            self._change_font_size(0, reset=True)
            return True
        return False

    def _change_font_size(self, step, reset=False):
        size = 11 if reset else self._font_size + step
        if size < 6 or size > 24:
            return
        self._font_size = size
        css = f"textview {{ font-size: {size}pt; }}"
        self._zoom_provider.load_from_data(css.encode())

    # ---------------- about ----------------
    def _find_data(self, name):
        for d in DATA_DIRS:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        here = os.path.dirname(os.path.abspath(__file__))
        for base in (os.path.join(here, ".."), here):
            p = os.path.join(base, name)
            if os.path.exists(p):
                return p
        return None

    def _hand_cursor(self, widget, on):
        win = widget.get_window()
        if win is not None:
            display = widget.get_display()
            win.set_cursor(
                Gdk.Cursor.new_from_name(display, "pointer") if on else None
            )

    def _show_about(self):
        dlg = Gtk.Dialog(title="About Sugoi! Docker", transient_for=self.win, modal=True)
        dlg.set_resizable(False)
        content = dlg.get_content_area()
        content.set_border_width(24)
        content.set_spacing(10)

        accent = ACCENT_DARK if self.dark else ACCENT_LIGHT

        logo_path = self._find_data("VSLogo_White.png" if self.dark else "VSLogo_Black.png")
        if logo_path:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 300, -1, True)
            img = Gtk.Image.new_from_pixbuf(pb)
            content.pack_start(img, False, False, 0)

        name = Gtk.Label()
        name.set_markup(f"<b><span size='x-large'>Sugoi! Docker</span></b>")
        name.set_halign(Gtk.Align.CENTER)
        content.pack_start(name, False, False, 0)

        ver = Gtk.Label(label=f"Version {__version__}")
        ver.get_style_context().add_class("dim-label")
        ver.set_halign(Gtk.Align.CENTER)
        content.pack_start(ver, False, False, 0)

        content.pack_start(Gtk.Separator(), False, False, 8)

        studio = Gtk.Label()
        studio.set_markup(
            f"Made by <b><span foreground='{accent}'>{STUDIO_NAME}</span></b> Studio"
        )
        studio.set_halign(Gtk.Align.CENTER)
        content.pack_start(studio, False, False, 0)

        tag = Gtk.Label(label=TAGLINE)
        tag.get_style_context().add_class("dim-label")
        tag.set_justify(Gtk.Justification.CENTER)
        tag.set_halign(Gtk.Align.CENTER)
        tag.set_max_width_chars(40)
        content.pack_start(tag, False, False, 0)

        gh_btn = Gtk.Button()
        gh_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        gh_path = self._find_data("github-mark.svg")
        if gh_path:
            gh_img = Gtk.Image.new_from_file(gh_path)
            gh_img.set_pixel_size(16)
            gh_inner.pack_start(gh_img, False, False, 0)
        gh_inner.pack_start(Gtk.Label(label="github.com/VANTASEED"), False, False, 0)
        gh_btn.add(gh_inner)
        gh_btn.set_halign(Gtk.Align.CENTER)
        gh_btn.set_margin_top(10)
        gh_btn.connect(
            "clicked",
            lambda _b: Gtk.show_uri_on_window(dlg, GITHUB_URL, Gdk.CURRENT_TIME),
        )
        content.pack_start(gh_btn, False, False, 0)

        dlg.add_button("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, _r: d.destroy())
        dlg.show_all()

    def _append_colored(self, text):
        pal = dict(DARK_PALETTE if self.dark else LIGHT_PALETTE)
        pal.update(_XTERM_256)
        attrs = {"bold": False, "dim": False, "italic": False,
                 "underline": False, "fg": None, "bg": None}
        i, n = 0, len(text)
        while i < n:
            c = text[i]
            if c != "\x1b":
                end = text.find("\x1b", i)
                chunk_end = n if end == -1 else end
                self._insert_chunk(text[i:chunk_end], attrs)
                i = chunk_end
                continue

            if text[i + 1:i + 2] == "[":
                j = i + 2
                while j < n and not ("\x40" <= text[j] <= "\x7e"):
                    j += 1
                if j >= n:
                    break
                final, params = text[j], text[i + 2:j].split(";")
                i = j + 1
                if final == "m":
                    self._apply_sgr(attrs, params, pal)
            elif text[i + 1:i + 2] == "]":
                j = i + 2
                while j < n and text[j] != "\x07":
                    if text[j:j + 2] == "\x1b\\":
                        break
                    j += 1
                i = j + 2 if j < n else n
            else:
                i += 2

    def _apply_sgr(self, attrs, params, pal):
        p = []
        for x in params:
            if x and ":" in x:
                p.extend(x.split(":"))
            elif x:
                p.append(x)
        if not p:
            p = ["0"]
        i = 0
        while i < len(p):
            try:
                v = int(p[i])
            except ValueError:
                i += 1
                continue
            if v == 0:
                attrs.update(bold=False, dim=False, italic=False,
                             underline=False, fg=None, bg=None)
            elif v == 1:
                attrs["bold"] = True
            elif v == 2:
                attrs["dim"] = True
            elif v == 3:
                attrs["italic"] = True
            elif v == 4:
                attrs["underline"] = True
            elif v == 22:
                attrs["bold"] = attrs["dim"] = False
            elif v == 23:
                attrs["italic"] = False
            elif v == 24:
                attrs["underline"] = False
            elif 30 <= v <= 37:
                attrs["fg"] = pal[v - 30]
            elif 90 <= v <= 97:
                attrs["fg"] = pal[v - 90 + 8]
            elif v == 39:
                attrs["fg"] = None
            elif 40 <= v <= 47:
                attrs["bg"] = pal[v - 40]
            elif 100 <= v <= 107:
                attrs["bg"] = pal[v - 100 + 8]
            elif v == 49:
                attrs["bg"] = None
            elif v == 38:
                i = self._truecolor(attrs, p, i, "fg", pal)
                continue
            elif v == 48:
                i = self._truecolor(attrs, p, i, "bg", pal)
                continue
            i += 1

    def _truecolor(self, attrs, p, i, slot, pal):
        mode = p[i + 1] if i + 1 < len(p) else ""
        if mode == "5" and i + 2 < len(p):
            try:
                attrs[slot] = pal.get(int(p[i + 2]) % 256)
            except ValueError:
                pass
            return i + 3
        if mode == "2" and i + 4 < len(p):
            try:
                r, g, b = (int(p[i + 2]) & 255, int(p[i + 3]) & 255, int(p[i + 4]) & 255)
                attrs[slot] = f"#{r:02x}{g:02x}{b:02x}"
            except ValueError:
                pass
            return i + 5
        return i

    def _insert_chunk(self, chunk, attrs):
        key = (attrs["bold"], attrs["dim"], attrs["italic"],
               attrs["underline"], attrs["fg"], attrs["bg"])
        tag = self._tags.get(key)
        if tag is None:
            tag = self.buf.create_tag(None)
            props = {}
            if attrs["bold"]:
                props["weight"] = Pango.Weight.BOLD
            if attrs["dim"]:
                props["foreground-alpha"] = 45000
            if attrs["italic"]:
                props["style"] = Pango.Style.ITALIC
            if attrs["underline"]:
                props["underline"] = Pango.Underline.SINGLE
            if attrs["fg"]:
                props["foreground"] = attrs["fg"]
            if attrs["bg"]:
                props["background"] = attrs["bg"]
            for k, val in props.items():
                tag.set_property(k, val)
            self._tags[key] = tag
        self.buf.insert_with_tags(self.buf.get_end_iter(), chunk, tag)

    # ---------------- status ----------------
    def refresh_status(self):
        def worker():
            try:
                active = subprocess.run(
                    ["systemctl", "is-active", "docker"],
                    capture_output=True, text=True).stdout.strip()
            except Exception:
                active = "unknown"
            try:
                enabled = subprocess.run(
                    ["systemctl", "is-enabled", "docker"],
                    capture_output=True, text=True).stdout.strip()
            except Exception:
                enabled = "unknown"
            GLib.idle_add(self._set_status, active, enabled)

        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, active, enabled):
        if active == "active":
            dot = "#2ec27e" if self.dark else "#1f8a4c"
        elif active == "failed":
            dot = "#ff6b6b" if self.dark else "#c01c28"
        else:
            dot = "#888888"
        self.status_lbl.set_markup(
            f"<span foreground='{dot}'><small>\u25cf</small></span>"
            f" {active} \u00b7 boot: {enabled}"
        )
        return False


if __name__ == "__main__":
    app = DockerCtlGUI()
    app.run()
