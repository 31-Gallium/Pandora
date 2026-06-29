# `media.py` (hub_modules) Summary

## Role in Architecture
A highly complex Hub Module responsible for displaying currently playing media metadata, album art, and reacting to audio levels with various audio visualizers.

## Key Classes and Functions
- **`MediaHub(BaseHubModule)`**:
  - Interacts heavily with `MediaSessionManager` (WinRT background daemon) to get track info, album art, and audio peaks.
  - **Visualizers**: Implements several complex audio-reactive visualizers in `draw()`:
    - *Edge Ring EQ*: A wavy, liquid circular line graph that deforms based on `audio_peak`.
    - *8-Bit Mosaic / Voxel Wiggle*: Pixelates the album art into a grid of blocks and optionally simulates 2D physics/gravity on the blocks based on the audio beat (`eased_peak`).
    - *Breathing Blur / Size Pulsing*: Scales the album art smoothly to the beat of the music.
  - Handles caching and extracting dominant colors (`_extract_color`) from the album art to color-match the UI.
  - Overrides the Halo menu tools (using Spacebar) to inject media controls (Prev, Next, Timeline, Volume) into the outer ring.
  - Handles mouse scroll wheel logic specifically for scrubbing the track timeline or adjusting app-specific volume.

## Dependencies and Interactions
- Heavily relies on `utils.py` / `MediaSessionManager`.
- Deeply integrates with `Halo` UI to hijack input and change radial options.
- Uses math and time extensively for 60fps animations.
