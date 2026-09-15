import difflib
import time

from logging import Logger
from typing import Optional, List

from plexapi import exceptions
from plexapi.library import MusicSection
from plexapi.server import PlexServer
from plexapi.audio import Artist, Track, Album
from plexapi.exceptions import NotFound
from plexapi.playlist import Playlist
from plexapi.playqueue import PlayQueue

from askplex import text_utils
from .text_utils import TextUtils


class PlexApiUtils:
    """
    Provides utility functions for interacting with the Plex API.
    Includes artist, track, album, and playlist search functions.
    """

    def __init__(self, logger: Logger, text_utils: TextUtils) -> None:
        """
        Initializes the Plex API utilities with a logger.
        Args:
            logger (Logger): The logger instance to be used for logging.
        """
        self.logger = logger
        self.text = text_utils

    def get_artist(self, section: MusicSection, name: str) -> Optional[Artist]:
        """
        Search for and retrieve an artist by name from a MusicSection.

        Args:
            section (MusicSection): The MusicSection to search in.
            name (str): The artist name to search for.

        Returns:
            Optional[Artist]: The found artist, or None if not found.
        """
        self.logger.debug(f"Searching for artist with original name: '{name}'")

        original_name = name
        normalized_name = self.text._normalize_query(name)

        # searchArtists(title) is the quickest method by far so try that with both name variants first
        timer = time.time()
        matches = section.searchArtists(title=original_name)
        self.logger.debug(f"Timer - title search on '{original_name}': " + str(time.time() - timer))
        if matches:
            self.logger.debug(f"Found artist with exact title match: '{original_name}'")
            return matches[0]

        timer = time.time()
        matches = section.searchArtists(title=normalized_name)
        self.logger.debug(f"Timer - title search on '{normalized_name}': " + str(time.time() - timer))
        if matches:
            self.logger.debug(f"Found artist with exact title match: '{normalized_name}'")
            return matches[0]

        # If searchArtists(title fails, try searchArtists(title__icontains)
        timer = time.time()
        match = section.searchArtists(title__icontains=original_name)
        self.logger.debug(f"Timer - title__icontains search on '{original_name}': " + str(time.time() - timer))
        if match:
            self.logger.debug(f"Found artist with title__icontains match: '{original_name}'")
            return match[0]

        timer = time.time()
        match = section.searchArtists(title__icontains=normalized_name)
        self.logger.debug(f"Timer - title__icontains search on '{normalized_name}': " + str(time.time() - timer))
        if match:
            self.logger.debug(f"Found artist with title__icontains match: '{normalized_name}'")
            return match[0]

        # Finally, try icontains on titleSort
        timer = time.time()
        match = section.searchArtists(titleSort__icontains=original_name)
        self.logger.debug(f"Timer - titleSort__icontains search on '{original_name}': " + str(time.time() - timer))
        if match:
            self.logger.debug(f"Found artist with titleSort__icontains match: '{original_name}'")
            return match[0]

        timer = time.time()
        match = section.searchArtists(titleSort__icontains=normalized_name)
        self.logger.debug(f"Timer - titleSort__icontains search on '{normalized_name}': " + str(time.time() - timer))
        if match:
            self.logger.debug(f"Found artist with titleSort__icontains match: '{normalized_name}'")
            return match[0]

        self.logger.debug(f"No match found for artist: '{original_name}' (normalized: '{normalized_name}')")
        return None

    def get_track(self, section: MusicSection, artist: str, title: str) -> Optional[Track]:
        """
        Search for an retrieve a Track by title and artist

        Args:
            section (MusicSection): The MusicSection to search in.
            artist (str): The artist name to search for.
            title (str): The track title to search for.

        Returns:
            Optional[Track]: The found track, or None if not found.
        """

        matches = section.searchTracks(title=title)
        self.logger.debug(f"Track matches: {matches}")
        if matches:
            return matches[0]

        return None

    def get_track_by_artist(self, artist: Artist, title: str) -> Optional[Track]:
        """
        Search for and retrieve a Track by title from an Artist.

        Args:
            artist (Artist): The artist to search for the track in.
            title (str): The track title to search for.

        Returns:
            Optional[Track]: The found track, or None if not found.
        """
        original_title = title
        normalized_title = self.text._normalize_query(original_title)

        self.logger.debug(f"Searching for track with original title: '{original_title}'")
        try:
            track = artist.track(title=original_title)
            return track
        except NotFound as exception:
            self.logger.error(f"Track not found. '{exception}'")
            pass

        self.logger.debug(f"Searching for track with normalized title: '{normalized_title}'")
        try:
            track = artist.track(title=normalized_title)
            return track
        except NotFound as exception:
            self.logger.error(f"Track not found. '{exception}'")
            pass

        self.logger.debug("Fetching all tracks for the artist")
        # Fetch all tracks for the artist
        all_tracks = artist.tracks()
        self.logger.debug(f"All tracks: {all_tracks}")
        # Filter using a precise match or a case-insensitive check
        self.logger.debug(f"Filtering tracks for title: '{title}'")
        for t in all_tracks:
            self.logger.debug(f"Track title: '{self.text.strip_specials(t.title.lower())}', comparing to '{original_title.lower()}' and '{normalized_title.lower()}'")
            if (original_title.lower() in self.text.strip_specials(t.title.lower())
                    or normalized_title.lower() in self.text.strip_specials(t.title.lower()))\
                    or self.text.strip_specials(original_title.lower()) in self.text.strip_specials(t.title.lower())\
                    or self.text.strip_specials(normalized_title.lower()) in self.text.strip_specials(t.title.lower()):
                self.logger.debug(f"Found track: '{t}'")
                return t

        return None

    def get_album(self, artist: Artist, title: str) -> Optional[Album]:
        """
        Search for and retrieve an Album by title from an Artist.

        Args:
            artist (Artist): The artist to search for the album in.
            title (str): The album title to search for.

        Returns:
            Optional[Album]: The found album, or None if not found.
        """

        try:
            album = artist.album(title=title)
            return album
        except NotFound:
            pass

        albums = artist.albums(title__icontains=title)
        if albums:
            return albums[0]

        return None

    def get_playlist(self, server: PlexServer, title: str) -> Optional[Playlist]:
        """
        Search for and retrieve a Playlist by name from a PlexServer.

        Args:
            server (PlexServer): The server to search in.
            title (str): The playlist name to search for.

        Returns:
            Optional[Playlist]: The found playlist, or None if not found.
        """

        try:
            return server.playlist(title)
        except NotFound:
            pass

        playlists = server.search(query=title, mediatype="playlist")
        if playlists:
            return playlists[0]

        return None

    def get_random_tracks(self, section: MusicSection, maxresults: int) -> List[Track]:
        """
        Retrieve random tracks from a MusicSection.

        Args:
            section (MusicSection): The target MusicSection.
            maxresults (int): The number of tracks to retrieve.

        Returns:
            List[Artist]: The retrieved tracks.
        """

        return section.searchTracks(sort="random", maxresults=maxresults)

    def get_random_tracks_by_artist(self, section: MusicSection, maxresults: int, artist: Artist) -> List[Track]:
        """
        Retrieve random tracks by a specified artist from a MusicSection.

        Args:
            section (MusicSection): The target MusicSection.
            maxresults (int): The number of tracks to retrieve.
            artist (Artist): The target artist.

        Returns:
            List[Artist]: The retrieved tracks.
        """

        return section.search(
            libtype='track',
            sort='random',
            maxresults=maxresults,
            filters={'artist.id': artist.ratingKey}
        )

    def get_random_tracks_by_genre(self, section: MusicSection, maxresult: int, genre: str) -> List[Track]:
        """
        Retrieve random tracks by a specified genre from a MusicSection.

        Args:
        section (MusicSection): The target MusicSection.
        maxresults (int): The number of tracks to retrieve.
        genre (str): The target genre.

        Returns:
            List[Artist]: The retrieved tracks.
        """
        return section.search(libtype='track', sort='random', maxresults=maxresult, filters={'genre': genre})
        # section.searchTracks(sort='random', maxresults=maxresult, style=genre))

    def get_nearby_tracks(self, server: PlexServer, maxresult: int, track: Track) -> List[Track]:
        return self.get_similar_tracks_by_metadata(server, track, maxresult)

    def get_similar_tracks_by_metadata(self, plex_server, seed_track, target_count=40) -> List[Track]:
        """
        Bypasses the clientless PlayQueue system entirely.
        Directly extracts metadata-matched track objects from the Plex Database.

        :param plex_server: Your active PlexServer instance.
        :param seed_track: The Track object used to anchor the mix.
        :param target_count: The exact number of unique Track objects you want returned.
        :return: A Python list containing exclusively plexapi.audio.Track objects.
        """
        tracks_list: List[Track] = [seed_track]  # Start the list with your initial song
        seen_keys = {seed_track.ratingKey}

        # Get the library section to use for looking up full artist records
        music_section = plex_server.library.section(seed_track.librarySectionTitle)

        # 1. Fetch the Parent Artist object
        seed_artist = seed_track.artist()
        if not seed_artist:
            return tracks_list

        # 2. Grab Plex's text-metadata matched "Similar Artists" list property
        similar_artists_summary = seed_artist.similar

        # 3. Pull tracks from similar artists until we reach our target count
        if similar_artists_summary:
            for summary in similar_artists_summary:
                if len(tracks_list) >= target_count:
                    break

                try:
                    # CRUCIAL FIX: Fetch the complete Artist object from the library section
                    # to unlock the database methods like .tracks()
                    full_artist: Artist = music_section.get(summary.tag)

                    # Extract tracks belonging to this fully inflated artist object
                    for track in full_artist.tracks():
                        if track.ratingKey not in seen_keys:
                            tracks_list.append(track)
                            seen_keys.add(track.ratingKey)

                        if len(tracks_list) >= target_count:
                            break
                except Exception:
                    # Skip if the similar artist isn't found in your local local library
                    continue

        # 4. Fallback: If your library is small and we need more tracks, pull from the same Genre
        if len(tracks_list) < target_count and hasattr(seed_track.album(), 'genres'):
            for genre_obj in seed_track.album().genres:
                genre_matches = music_section.search(filters={'album.genre': genre_obj.tag}, libtype='track')

                for track in genre_matches:
                    if isinstance(track, Track) and track.ratingKey not in seen_keys:
                        tracks_list.append(track)
                        seen_keys.add(track.ratingKey)
                    if len(tracks_list) >= target_count:
                        break

        return tracks_list[:target_count]

    def get_track_fuzzy(self, music_section: MusicSection, artist_name: str, track_title: str, cutoff: float = 0.5) -> Optional[Track]:
        """
        Broadens track matching via Python fuzzy matching logic.

        :param music_section: The active Music Library Section.
        :param artist_name: Expected artist string (e.g., "Daft Punk").
        :param track_title: Expected track title (e.g., "Around the World").
        :param cutoff: Fuzziness threshold (0.0 to 1.0). 0.5 is very forgiving, 0.8 is strict.
        :return: The best matching Plex Track object or None.
        """
        # Step 1: Broaden the initial query by searching only for the Artist name
        # This completely bypasses track-level punctuation mismatches
        potential_tracks: List[Track] = []

        # Try an exact artist match first to get a manageable track list
        artists = music_section.search(title=artist_name, libtype='artist')

        if not artists:
            # If the artist name itself has a typo, pull the top 100 recent tracks as a last resort
            potential_tracks = music_section.search(libtype='track', maxresults=100)
        else:
            # Gather every single track belonging to that matched artist
            for artist in artists:
                potential_tracks.extend(artist.tracks())

        # Step 2: Calculate the similarity ratio for track titles using Python's difflib
        best_match: Optional[Track] = None
        highest_ratio: float = 0.0

        # Normalize strings for comparison (lowercase)
        target_title_clean = track_title.lower().strip()

        for track in potential_tracks:
            track_title_clean = track.title.lower().strip()

            # Calculate similarity (evaluates partial additions, case, edits, and brackets)
            ratio = difflib.SequenceMatcher(None, target_title_clean, track_title_clean).ratio()

            # If this match is closer than previous loops, keep it
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = track

        # Step 3: Enforce your custom fuzziness threshold
        if highest_ratio >= cutoff:
            self.logger.debug(f"Fuzzy Match Success ({int(highest_ratio*100)}% Match): '{best_match.title}'")
            return best_match

        self.logger.debug(f"No match found above threshold. Best attempt was {int(highest_ratio*100)}% on '{best_match.title if best_match else 'None'}'")
        return None