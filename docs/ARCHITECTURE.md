# Architecture

`app.py` owns application state and the loopback HTTP server. HTTP workers enqueue
device operations; the audio loop owns PortAudio and Core Audio COM objects.
`windows.py` runs native windows through pywebview on the GUI thread; `desktop.py`
handles the tray and Windows startup integration.

`engine.py` routes 48 kHz audio in 480-sample blocks. The microphone chain uses
high-pass filtering, optional echo cancellation, DeepFilterNet, gates, dry/wet blending,
and mute. The speaker chain filters incoming audio and feeds the echo reference.
`ladspa_df.py` hosts the native plugin; `mixer.py` contains the signal utilities.

The two HTML interfaces share translation dictionaries and an HTTP helper. Status
values are `stopped`, `running`, `waiting`, and `error` in every language. The language
setting may be English, Brazilian Portuguese, or automatic based on the system.

The loopback API is an internal implementation detail, not a stable public API.
See SECURITY.md for its trust boundary and diagnostic privacy behavior.
