#ifndef WAYLAND_SUPPORT_H
#define WAYLAND_SUPPORT_H

#include <wayland-client.h>

struct wl_display* init_wayland_display(void);

void cleanup_wayland_display(struct wl_display* display);

#endif
