from lyricsgenius.song import Song
from lyricsgenius import Genius
from .config import GENIUS_ACCESS_TOKEN


genius = Genius(GENIUS_ACCESS_TOKEN,
                timeout=10,
                retries=5,
                verbose=False)


def get_lyrics(track_name):
    track: Song = genius.search_song(title=track_name,  get_full_info=False)
    if track is None:
        return
    lyrics: str = track.lyrics\
        .replace("\n\n", "\n")\
        .replace("EmbedShare URLCopyEmbedCopy", "")\
        .replace("[", "**[")\
        .replace("]", "]**")
    return lyrics
