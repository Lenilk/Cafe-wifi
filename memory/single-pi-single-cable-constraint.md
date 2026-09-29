---
name: single-pi-single-cable-constraint
description: "Hard design constraint — one Raspberry Pi, one LAN cable into the café Wi-Fi router, plug-and-play; no separate management network"
metadata:
  node_type: memory
  pinned: false
  originSessionId: 4ec482b1-787a-40f3-9cbf-67b87d7eee75
  modified: 2026-09-29T16:27:16.590Z
---

The user requires that the Cafe-wifi product is a single Raspberry Pi that works by plugging one LAN cable from the café's Wi-Fi router into it — nothing else. Because of this, the management path (SSH, Admin Panel) cannot be moved to a separate interface, VLAN, or L2 segment; customers and the admin always share the same L2 as the Pi. The user rejected "separate the management interface from the customer L2" as a fix for review finding R2-03 (2026-09-29).

When proposing security fixes, do not suggest extra hardware, a second NIC/interface, or VLAN separation. Work within one shared L2: host firewall rules (e.g. dropping IPv6 input), strong authentication (the user plans to switch SSH to key-only with `PasswordAuthentication no` later), rate limiting, or cryptographic overlays such as WireGuard that run over the same cable. Note that IP/MAC allowlists on a shared L2 can be spoofed by customers, so present them as hurdles, not real separation.
