# tv-art

Turn any image into art for a Samsung Frame TV and send it to the TV over wifi.

The page crops or letterboxes your image to 3840x2160, the Frame's art mode resolution. You can download the result as a JPEG or push it straight to the TV.

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Use

```
.venv/bin/python serve.py
```

Open http://localhost:8000, then drop, paste or pick an image. Choose a mode:

- **Crop to fill** fills the screen. Drag the preview to pick which part to keep.
- **Fit, blurred background** shows the whole image over a blurred copy of itself.
- **Fit, solid background** shows the whole image on a colour you pick.

The zoom slider tightens the framing.

The TV field lists the Frames on your network. When the page loads, the server asks every address on your subnet for Samsung's TV info (port 8001, `/api/v2/`) and keeps the ones that report `FrameTVSupport`. That takes about a second. Pick one, or type an IP if yours isn't listed, for example because it sits outside your /24. The page remembers your choice. Hit Rescan if the TV was off when the page loaded.

**Send to TV** uploads the image with no matte and puts it on screen. The first send shows an Allow prompt on the TV. Accept it with the remote and the TV remembers the approval, so later sends don't ask again. A log under the controls shows each step as it happens. Storing a 4K image takes the TV a few seconds.

Without the server you can open `index.html` directly. Only the download button works that way. Upload the file with the SmartThings app or a USB stick.

## Caveats

- This uses the TV's undocumented art-app WebSocket API through [samsungtvws](https://github.com/xchwarze/samsung-tv-ws-api). Samsung has broken it with firmware updates before. It works on a 2024 43" Frame (QE43LS03DAUXXU).
- On macOS, Local Network privacy blocks Python from reaching the TV when it runs inside tmux. Start `serve.py` from a plain terminal window, and allow the terminal and Python under System Settings > Privacy & Security > Local Network.
- Every send adds a new image to the TV. Delete old ones from the TV's art mode menu when storage gets full.

## License

MIT
