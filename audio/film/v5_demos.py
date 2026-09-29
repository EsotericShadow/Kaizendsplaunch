"""Entry point named in film/v5/TREATMENT.md (sections 3 and 8): the v5 demo build lives in song_v5.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from song_v5 import main  # noqa: E402

if __name__ == "__main__":
    main()
