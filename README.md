# GNOME Wallpaper Engine

GNOME Wallpaper Engine is a lightweight, GPU-accelerated dynamic wallpaper solution for Linux. It uses GStreamer for video playback and GTK3 to automatically detect your desktop's workarea and scale the video to perfectly fit your screen—giving you a full-featured animated wallpaper experience similar to Wallpaper Engine.

## Features

- **Dynamic Video Wallpaper:** Set a video as your desktop wallpaper.
- **Automatic Scaling:** Detects your monitor's workarea and scales the video to fill your screen.
- **GPU-Accelerated:** Leverages GStreamer for efficient, hardware-accelerated playback.
- **Lightweight:** Designed to have minimal impact on system resources.
- **Wayland Support:** Yes!! You have heard that right XD, this is the first time finally adding Wayland support. However... there's no multi-monitor support as it only works for a single monitor for now.

## Prerequisites

Before you get started, ensure you have the following installed:

- **Python 3.x**
- **GStreamer 1.0** (and necessary plugins, e.g., `gst-plugins-base`, `gst-plugins-good`, etc.)
- **GTK 3**
- **Wayland development libraries** (only needed for Wayland users)

For Ubuntu/Debian systems, you can install the required packages with:

```bash
sudo apt install python3-gi python3-gst-1.0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gir1.2-gst-plugins-base-1.0 gir1.2-gtk-3.0 wayland-protocols libwayland-dev
```

## Installation

### For Wayland Users:
If you're using Wayland, you need to compile the Wayland stub before running the script:

```bash
gcc main.c -o main $(pkg-config --cflags --libs wayland-client)
gcc wayland_stub.c -o wayland_stub $(pkg-config --cflags --libs wayland-client)
gcc -c wayland_support.c $(pkg-config --cflags wayland-client)
```

Then, make the script executable and run it:

```bash
chmod +x wallpaper.py
./wallpaper.py
```

Alternatively, you can set it up to start automatically using a `.desktop` file (see below).

### For X11 Users:
No additional compilation is needed. Just make the script executable:

```bash
chmod +x wallpaper.py
```

Then run:

```bash
./wallpaper.py
```

## Usage

1. **Place your video file:**
   
   Make sure you have your video file at `~/Videos/wallpaper.mp4`. You can change this path in the script if needed.

2. **Run the script:**

   ```bash
   ./wallpaper.py
   ```

3. **Auto-Start on Login:**

   To run the wallpaper automatically on startup, copy the provided desktop entry (or create one) to your autostart directory:
   
   ```bash
   mkdir ~/.config/autostart/ && nano video-wallpaper.desktop && cp video-wallpaper.desktop ~/.config/autostart/
   ```

   *Example `video-wallpaper.desktop` content:*

   ```ini
   [Desktop Entry]
   Type=Application
   Name=Video Wallpaper
   Comment=Sets a video as the desktop wallpaper on startup
   Exec=/full/path/to/gnome-wallpaper-engine/wallpaper.py
   X-GNOME-Autostart-enabled=true
   Terminal=false
   ```

## Contributing

Contributions, issues, and feature requests are welcome! Please feel free to check out the [issues page](https://github.com/Techlm77/gnome-wallpaper-engine/issues) or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

Enjoy a dynamic, animated wallpaper on your GNOME desktop!
