#include <stdlib.h>

#ifdef WAYLAND_SUPPORT
#include "wayland_support.h"
#endif

#ifdef X11_SUPPORT
#include <X11/Xlib.h>
#endif

int main(int argc, char *argv[]) {
    const char* wayland_display = getenv("WAYLAND_DISPLAY");
    if (wayland_display) {
#ifdef WAYLAND_SUPPORT
        struct wl_display* display = init_wayland_display();
        if (display) {
            cleanup_wayland_display(display);
        }
#endif
    }
    else {
#ifdef X11_SUPPORT

#endif
    }
    return 0;
}
