#!/usr/bin/env python3
import os
import sys
import subprocess
import gi
import socket
import threading
import tempfile

gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gst, Gtk, Gdk, GLib, GdkPixbuf

SOCKET_PATH = "/tmp/wallpaper.sock"

def send_ipc_command(cmd):
    """Send a command (string) to the wallpaper process via IPC."""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(SOCKET_PATH)
        s.sendall(cmd.encode('utf-8'))
        s.close()
    except Exception as e:
        print("Error sending IPC command:", e)

class WallpaperIPCServer(threading.Thread):
    """A simple IPC server that listens on a Unix domain socket for commands."""
    def __init__(self, wallpaper):
        threading.Thread.__init__(self)
        self.wallpaper = wallpaper
        self.daemon = True
        self.sock_path = SOCKET_PATH
        if os.path.exists(self.sock_path):
            os.remove(self.sock_path)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.sock_path)
        self.server.listen(5)

    def run(self):
        while True:
            try:
                conn, _ = self.server.accept()
                data = conn.recv(1024)
                if data:
                    cmd = data.decode('utf-8').strip()
                    parts = cmd.split("|")
                    if parts[0] == "update_video" and len(parts) > 1:
                        self.wallpaper.update_video(parts[1])
                    elif parts[0] == "play":
                        self.wallpaper.play()
                    elif parts[0] == "pause":
                        self.wallpaper.pause()
                    elif parts[0] == "stop":
                        self.wallpaper.stop()
                    elif parts[0] == "volume" and len(parts) > 1:
                        try:
                            vol = float(parts[1])
                            self.wallpaper.player.set_property("volume", vol)
                        except:
                            pass
                conn.close()
            except Exception as e:
                print("IPC server error:", e)

class VideoWallpaper(Gtk.Window):
    def __init__(self, video_path=None):
        Gtk.Window.__init__(self, title="Video Wallpaper")
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)

        if os.environ.get("WAYLAND_DISPLAY"):
            try:
                subprocess.run(["./wayland_stub"], check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print("Error executing Wayland stub:", e.stderr)
            self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        else:
            self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)

        display = Gdk.Display.get_default()
        monitor = display.get_monitor(0)
        workarea = monitor.get_geometry()
        self.width = workarea.width
        self.height = workarea.height
        self.set_default_size(self.width, self.height)
        self.move(workarea.x, workarea.y)
        self.set_keep_below(True)
        self.stick()
        GLib.timeout_add(500, self.push_below)

        self.fixed = Gtk.Fixed()
        self.add(self.fixed)

        Gst.init(None)
        self.player = Gst.ElementFactory.make("playbin", "player")
        if not self.player:
            print("Error: Could not create playbin element.")
            exit(-1)

        if video_path is None:
            video_path = os.path.expanduser("~/Videos/wallpaper.mp4")
        if not os.path.exists(video_path):
            print("Error: Video file not found:", video_path)
            exit(-1)
        self.player.set_property("uri", "file://" + video_path)

        video_filter_bin = Gst.Bin.new("video_filter_bin")
        videoscale = Gst.ElementFactory.make("videoscale", "videoscale")
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        if not videoscale or not capsfilter:
            print("Error: Could not create videoscale or capsfilter")
            exit(-1)
        caps = Gst.Caps.from_string(f"video/x-raw, width={self.width}, height={self.height}, pixel-aspect-ratio=1/1")
        capsfilter.set_property("caps", caps)
        video_filter_bin.add(videoscale)
        video_filter_bin.add(capsfilter)
        if not videoscale.link(capsfilter):
            print("Error: Failed to link videoscale to capsfilter")
            exit(-1)
        ghost_sink = Gst.GhostPad.new("sink", videoscale.get_static_pad("sink"))
        video_filter_bin.add_pad(ghost_sink)
        ghost_src = Gst.GhostPad.new("src", capsfilter.get_static_pad("src"))
        video_filter_bin.add_pad(ghost_src)
        self.player.set_property("video-filter", video_filter_bin)

        possible_sinks = ["gtksink", "vaapisink", "glimagesink", "autovideosink"]
        videosink = None
        for sink_name in possible_sinks:
            videosink = Gst.ElementFactory.make(sink_name, "videosink")
            if videosink:
                break
        if videosink:
            if any(prop.name == "force-aspect-ratio" for prop in videosink.list_properties()):
                videosink.set_property("force-aspect-ratio", False)
            self.player.set_property("video-sink", videosink)
        else:
            print("Error: No suitable video sink found.")
            exit(-1)
        try:
            video_widget = videosink.props.widget
            video_widget.set_hexpand(True)
            video_widget.set_vexpand(True)
            video_widget.set_size_request(self.width, self.height)
            self.fixed.put(video_widget, 0, 0)
        except Exception as e:
            print("Error: Could not retrieve widget from videosink:", e)

        self.show_all()

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)
        self.player.set_state(Gst.State.PLAYING)

    def start_ipc_server(self):
        self.ipc_server = WallpaperIPCServer(self)
        self.ipc_server.start()

    def push_below(self):
        if self.get_window():
            self.get_window().lower()
        return True

    def on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("GStreamer Error:", err, debug)
            self.player.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.EOS:
            self.player.seek_simple(Gst.Format.TIME,
                                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                    0)
        return True

    def on_destroy(self, *args):
        self.player.set_state(Gst.State.NULL)
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        Gtk.main_quit()

    def update_video(self, video_path):
        if os.path.exists(video_path):
            self.player.set_state(Gst.State.NULL)
            self.player.set_property("uri", "file://" + video_path)
            self.player.set_state(Gst.State.PLAYING)
        else:
            print("Error: Video file not found:", video_path)

    def pause(self):
        self.player.set_state(Gst.State.PAUSED)

    def play(self):
        self.player.set_state(Gst.State.PLAYING)

    def stop(self):
        self.player.set_state(Gst.State.NULL)

class ControlPanel(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Wallpaper Control Panel")
        self.set_border_width(10)
        self.set_default_size(600, 400)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(hbox, False, False, 0)

        file_button = Gtk.Button(label="Select Video")
        file_button.connect("clicked", self.on_select_video)
        hbox.pack_start(file_button, False, False, 0)

        play_button = Gtk.Button(label="Play")
        play_button.connect("clicked", self.on_play)
        hbox.pack_start(play_button, False, False, 0)

        pause_button = Gtk.Button(label="Pause")
        pause_button.connect("clicked", self.on_pause)
        hbox.pack_start(pause_button, False, False, 0)

        stop_button = Gtk.Button(label="Stop")
        stop_button.connect("clicked", self.on_stop)
        hbox.pack_start(stop_button, False, False, 0)

        vol_label = Gtk.Label(label="Volume")
        hbox.pack_start(vol_label, False, False, 0)
        adjustment = Gtk.Adjustment(value=1, lower=0, upper=1, step_increment=0.1, page_increment=0.1, page_size=0)
        self.volume_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adjustment)
        self.volume_scale.set_digits(1)
        self.volume_scale.set_value(1)
        self.volume_scale.connect("value-changed", self.on_volume_changed)
        hbox.pack_start(self.volume_scale, True, True, 0)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(separator, False, False, 5)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrolled, True, True, 0)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.flowbox)

        self.populate_thumbnails()

    def on_select_video(self, widget):
        dialog = Gtk.FileChooserDialog(title="Select Video File", parent=self,
                                       action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        filter_video = Gtk.FileFilter()
        filter_video.set_name("Video Files")
        filter_video.add_mime_type("video/mp4")
        filter_video.add_mime_type("video/x-matroska")
        filter_video.add_pattern("*.mp4")
        filter_video.add_pattern("*.mkv")
        dialog.add_filter(filter_video)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            video_path = dialog.get_filename()
            send_ipc_command("update_video|" + video_path)
        dialog.destroy()

    def on_play(self, widget):
        send_ipc_command("play")

    def on_pause(self, widget):
        send_ipc_command("pause")

    def on_stop(self, widget):
        send_ipc_command("stop")

    def on_volume_changed(self, scale):
        vol = scale.get_value()
        send_ipc_command("volume|" + str(vol))

    def populate_thumbnails(self):
        video_dir = os.path.expanduser("~/Videos")
        try:
            video_files = [os.path.join(video_dir, f) for f in os.listdir(video_dir)
                           if f.lower().endswith(('.mp4', '.mkv'))]
        except Exception as e:
            print("Error scanning video directory:", e)
            video_files = []
        for video in video_files:
            thumbnail = self.create_thumbnail(video)
            if thumbnail:
                event_box = Gtk.EventBox()
                image = Gtk.Image.new_from_pixbuf(thumbnail)
                event_box.add(image)
                event_box.connect("button-press-event", self.on_thumbnail_clicked, video)
                self.flowbox.add(event_box)
        self.flowbox.show_all()

    def create_thumbnail(self, video_path):
        try:
            tmp_dir = tempfile.gettempdir()
            thumb_path = os.path.join(tmp_dir, os.path.basename(video_path) + ".png")
            cmd = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-ss", "00:00:01.000",
                "-vframes", "1",
                thumb_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumb_path, width=150, height=100, preserve_aspect_ratio=True)
            return pixbuf
        except Exception as e:
            print("Error creating thumbnail for", video_path, ":", e)
            return None

    def on_thumbnail_clicked(self, widget, event, video_path):
        send_ipc_command("update_video|" + video_path)

def is_wallpaper_running():
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(SOCKET_PATH)
        s.close()
        return True
    except:
        return False

def run_wallpaper_daemon():
    wallpaper = VideoWallpaper()
    wallpaper.start_ipc_server()
    wallpaper.connect("destroy", wallpaper.on_destroy)
    Gtk.main()

def run_control_panel():
    control_panel = ControlPanel()
    control_panel.connect("destroy", Gtk.main_quit)
    control_panel.show_all()
    Gtk.main()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--daemon":
            run_wallpaper_daemon()
        elif sys.argv[1] == "--control":
            run_control_panel()
        else:
            print("Usage: {} [--daemon | --control]".format(sys.argv[0]))
    else:
        if not is_wallpaper_running():
            subprocess.Popen([sys.executable, sys.argv[0], "--daemon"])
        run_control_panel()
