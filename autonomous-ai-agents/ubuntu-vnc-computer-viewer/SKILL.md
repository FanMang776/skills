---
name: ubuntu-vnc-computer-viewer
description: Use when connecting a LAN Ubuntu desktop into Hermes viewer.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux]
metadata:
  hermes:
    tags: [hermes, desktop-plugins, vnc, x11vnc, websockify, novnc, remote-desktop, ubuntu]
---

# Ubuntu VNC → Hermes Computer Viewer

## Goal

Make a LAN Ubuntu machine's physical desktop appear inside the Hermes Desktop
Computer pane (plugin: `hunterbohm/hermes-computer-viewer`, a layout fork of
`thomasbek3/hermes-bot-kit` computer-viewer).

## Architecture (memorize this)

```
Hermes Desktop plugin ──HTTP/WS──▶ websockify (:6080, noVNC web root)
                       ──TCP──────▶ x11vnc (:5900) ──▶ X display (often :1)
```

**The plugin can NOT talk to a raw VNC port.** It speaks WebSocket/noVNC.
Without websockify the user can paste `IP:5900` forever and it will never
connect — this is the #1 failure mode.

## Procedure

### 1. Install the plugin (Windows host)

- `curl -sL --ssl-no-revoke <raw plugin.js URL>` (this host ALWAYS needs
  `--ssl-no-revoke`) into `$HERMES_HOME/desktop-plugins/computer-viewer/plugin.js`
  (here: `C:/Users/cj/AppData/Local/hermes/desktop-plugins/`).
- User runs Ctrl+K → "Reload desktop plugins" (packaged builds have NO CDP
  port on 9222 — you cannot drive the plugin UI yourself; the user must type
  the VNC password anyway).

### 2. Start x11vnc on the Ubuntu box (via SSH, key auth)

- Find the real display and auth file — **do NOT assume `:0`**:
  `ls /tmp/.X11-unix/` and `ps wwwaux | grep Xorg` (the Xorg command line
  shows the true `-auth` path, typically `/run/user/1000/gdm/Xauthority`).
  An SSH session's `$DISPLAY` (e.g. `localhost:10.0`) is X11 forwarding —
  wrong target; `-auth guess` fails there.
- Password: `x11vnc -storepasswd` once (user types it).
- Launch (nohup into `~/.vnc/x11vnc.log`):
  `x11vnc -display :1 -auth /run/user/1000/gdm/Xauthority -forever -loop -noxdamage -repeat -rfbauth ~/.vnc/passwd -rfbport 5900 -shared`
- Success line in log: `The VNC desktop is:` and `PORT=5900`.
- GDM login-screen caveat: if the session may log out, x11vnc dies with the
  X session; the gdm Xauthority covers the greeter only via sudo.

### 3. Bridge with websockify (no sudo needed)

Sudo requires a password over SSH, so install websockify into a user venv.
On a locked-down/proxied box, plain `python3 -m venv` (bundled pip) can hang
the download — the working fallback:

```bash
python3 -m venv --without-pip ~/.vnc/wsenv
curl -sS https://bootstrap.pypa.io/get-pip.py -o ~/.vnc/get-pip.py
~/.vnc/wsenv/bin/python ~/.vnc/get-pip.py -q
~/.vnc/wsenv/bin/python -m pip install -q websockify
```

noVNC web root: download the release tarball on the Windows host
(`novnc/noVNC` tag tarball from GitHub), `scp -r` the extracted dir to
`~/.vnc/noVNC` (Ubuntu had no noVNC package installed).

Run it:
```bash
nohup ~/.vnc/wsenv/bin/websockify --web=$HOME/.vnc/noVNC 0.0.0.0:6080 localhost:5900 \
  >~/.vnc/websockify.log 2>&1 &
```
(No `--builtin-web` option in current websockify; `--web=` pointing at the
noVNC dir serves vnc.html.)

### 4. Verify from the Windows host before touching the UI

- `(echo > /dev/tcp/IP/5900)` and `curl -s http://IP:6080/vnc.html` → expect 200.
- Root URL returns a directory listing (python http.server style) if `--web`
  points at the wrong dir — check for `vnc.html`.

### 5. User fills the plugin dialog

- Endpoint picker: **Local** (LAN machine, not Cloud).
- OS toggle only has Mac/Windows (upstream has no Linux option — it's just
  instructional text; leave it alone).
- Computer address: **`http://IP:6080/vnc.html`** (classified as iframe mode,
  "Web viewer page — will be embedded"), password = the x11vnc password.

## Pitfalls

- Display number is frequently `:1` on modern GDM/Ubuntu, not `:0`.
- Wayland sessions are invisible to x11vnc — session must be "Ubuntu on Xorg"
  (check `ps` for Xorg vs Xwayland).
- `pkill -f websockify` over SSH can kill the SSH session's own process group
  and return exit 255 — the process still restarts fine on a second command.
- Long pip/venv commands over SSH: raise timeout; the box may be slow, and a
  timeout mid-install leaves a half venv (rm -rf and redo with the
  --without-pip path).
- systemd autostart units for x11vnc + websockify are the agreed follow-up
  after first successful connect (both currently die on reboot).
