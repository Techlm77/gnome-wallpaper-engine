#!/usr/bin/env python3
import os
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gst, Gtk, Gdk, GLib

class VideoWallpaper(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Video Wallpaper")

        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP)

        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        workarea = monitor.get_workarea()

        self.width = workarea.width
        self.height = workarea.height
        self.set_default_size(self.width, self.height)
        self.move(workarea.x, workarea.y)
        self.set_keep_below(True)

        GLib.timeout_add(500, self.push_below)

        self.fixed = Gtk.Fixed()
        self.add(self.fixed)

        Gst.init(None)
        self.player = Gst.ElementFactory.make("playbin", "player")
        if not self.player:
            print("Could not create playbin element.")
            exit(-1)

        video_path = os.path.expanduser("~/Videos/wallpaper.mp4")
        if not os.path.exists(video_path):
            print("Video file not found:", video_path)
            exit(-1)
        self.player.set_property("uri", "file://" + video_path)

        video_filter_bin = Gst.Bin.new("video_filter_bin")
        videoscale = Gst.ElementFactory.make("videoscale", "videoscale")
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        if not videoscale or not capsfilter:
            print("Could not create videoscale or capsfilter")
            exit(-1)

        caps = Gst.Caps.from_string(f"video/x-raw, width={self.width}, height={self.height}, pixel-aspect-ratio=1/1")
        capsfilter.set_property("caps", caps)

        video_filter_bin.add(videoscale)
        video_filter_bin.add(capsfilter)
        if not videoscale.link(capsfilter):
            print("Failed to link videoscale to capsfilter")
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
                print(f"Using video sink: {sink_name}")
                break

        if videosink:
            if any(prop.name == "force-aspect-ratio" for prop in videosink.list_properties()):
                videosink.set_property("force-aspect-ratio", False)
            self.player.set_property("video-sink", videosink)
        else:
            print("No suitable video sink found.")
            exit(-1)

        try:
            video_widget = videosink.props.widget
            video_widget.set_hexpand(True)
            video_widget.set_vexpand(True)
            video_widget.set_size_request(self.width, self.height)
            self.fixed.put(video_widget, 0, 0)
        except Exception as e:
            print("Could not retrieve widget from videosink:", e)

        self.show_all()

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message)

        self.player.set_state(Gst.State.PLAYING)

    def push_below(self):
        """Ensure the window stays below desktop icons."""
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
            self.player.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                0)
        return True

    def on_destroy(self, *args):
        print("Shutting down video wallpaper...")
        self.player.set_state(Gst.State.NULL)
        Gtk.main_quit()

if __name__ == "__main__":
    win = VideoWallpaper()
    win.connect("destroy", win.on_destroy)
    Gtk.main()
