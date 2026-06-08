#!/usr/bin/env python3
"""Entry point for the browser / mobile build (pygbag).

pygbag looks for a top-level `main.py` whose async loop it can drive inside the
browser's event loop. The game itself lives in `space_invaders.py` and runs the
same way on the desktop (`python3 space_invaders.py`).

Build the web version with:

    pip install pygbag
    pygbag main.py

then open the printed http://localhost:8000 URL (works on a phone browser too
once the build/ folder is hosted somewhere reachable).
"""

import asyncio

from space_invaders import main

if __name__ == "__main__":
    asyncio.run(main())
