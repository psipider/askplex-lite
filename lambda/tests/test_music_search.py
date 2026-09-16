"""
Test suite for MusicSearch class.
Tests against actual Plex server for local development and optimization.
"""
import sys
import os
import logging
import unittest
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plextreme import config
from plextreme import prompts
from plextreme.plex_connector import PlexConnector
from plextreme.music_search import MusicSearch
from plextreme.playlist_manager import PlaylistManager
from plextreme.playback_controller import PlaybackController
from plextreme.text_utils import TextUtils
from plextreme.plexapi_utils import PlexApiUtils
from tests.mocks.alexa_mocks import create_mock_handler_input


def mock_get_slot_value_v2(handler_input, slot_name):
    """
    Mock version of get_slot_value_v2 that works with our mock HandlerInput.
    """
    slot = handler_input.get_slot(slot_name)
    if slot:
        return slot
    return None


class TestMusicSearch(unittest.TestCase):
    """Test cases for MusicSearch class."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are used by all tests."""
        cls.logger = logging.getLogger(__name__)
        cls.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        cls.logger.addHandler(handler)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Reset the class variable to prevent interference between test runs
        from plextreme.plex_connector import PlexConnector
        PlexConnector._section = None
    
    def setUp(self):
        """Set up test fixtures for each test."""
        # Reset class variable before each test to ensure clean state
        from plextreme.plex_connector import PlexConnector
        PlexConnector._section = None
        
        self.handler_input = create_mock_handler_input("LaunchRequest")
        self.playlist_manager = PlaylistManager(self.logger, self.handler_input)
        self.plex_connector = PlexConnector(self.logger, self.handler_input, self.playlist_manager)
        self.playback_controller = PlaybackController(self.logger, self.handler_input, self.playlist_manager)
        self.text_utils = TextUtils(self.logger, self.handler_input)
        self.plexapi_utils = PlexApiUtils(self.logger, self.text_utils)
        self.music_search = MusicSearch(
            self.logger,
            self.handler_input,
            self.playlist_manager,
            self.playback_controller,
            self.plex_connector,
            self.text_utils,
            self.plexapi_utils
        )
        
        # Set up localization data
        self.handler_input.attributes_manager.request_attributes["_"] = {
            prompts.SKILL_INTENT_SLOTS_MISSING: "Please provide the required information.",
            prompts.PMS_CONNECTION_ERROR: "Unable to connect to Plex server.",
            prompts.PMS_SECTION_ERROR: "Error searching for section {}",
            prompts.PMS_SECTION_NOT_FOUND: "Music section not found.",
            prompts.PMS_CONNECTED: "Connection to Plex server successful.",
            prompts.PMS_TRACKS_SEARCH_EMPTY: "No tracks found.",
            prompts.PMS_ARTIST_SEARCH_ERROR: "Error searching for artist: {}",
            prompts.PMS_ARTIST_SEARCH_EMPTY: "Artist not found: {}",
            prompts.PMS_SONG_SEARCH_ERROR: "Error searching for song: {song} by {artist}",
            prompts.PMS_ALBUM_SEARCH_ERROR: "Error searching for album: {} by {artist}",
            prompts.PMS_ALBUM_SEARCH_EMPTY: "Album not found: {album} by {artist}",
            prompts.PMS_GENRE_SEARCH_ERROR: "Error searching for genre: {}",
            prompts.PMS_GENRE_SEARCH_EMPTY: "No tracks found for genre: {}",
            prompts.PMS_PLAYLIST_SEARCH_ERROR: "Error searching for playlist: {}",
            prompts.PMS_PLAYLIST_SEARCH_EMPTY: "Playlist not found: {}",
            prompts.PMS_SIMILAR_SEARCH_ERROR: "Error finding similar songs: {song} by {artist}",
            prompts.PMS_SIMILAR_SEARCH_EMPTY: "No similar songs found: {song} by {artist}",
            prompts.PMS_PLAYING: "Playing {}",
            prompts.PMS_PLNAME_RANDOM_MUSIC: "Random Music",
            prompts.PMS_PLNAME_MUSIC_BY_ARTIST: "Music by {}",
            prompts.PMS_PLNAME_SONG: "{song} by {artist}",
            prompts.PMS_PLNAME_ALBUM: "{album} by {artist}",
            prompts.PMS_PLNAME_MUSIC_BY_GENRE: "{} genre music",
            prompts.PMS_PLNAME_PLAYLIST: "Playlist: {}",
            prompts.PMS_PLNAME_SIMILAR: "Similar to {song} by {artist}",
        }
    
    def test_play_random_music(self):
        """Test playing random music."""
        print("\n=== Testing Play Random Music ===")
        
        # Ensure connection before testing
        success, response = self.plex_connector.connect_plex()
        if not success:
            self.fail(f"Failed to connect to Plex server: {response}")
        
        self.assertIsNotNone(PlexConnector._section, "Section should be set after connection")
        
        response = self.music_search.play_random_music()
        
        print(f"✓ Response generated: {response.output_speech if hasattr(response, 'output_speech') else 'N/A'}")
        
        # Check playlist was populated
        playlist = self.handler_input.attributes_manager.persistent_attributes["playback_info"]["playlist"]
        print(f"✓ Playlist size: {len(playlist)}")
        
        self.assertGreater(len(playlist), 0, "Playlist should contain tracks")
    
    def test_play_music_by_artist(self):
        """Test playing music by specific artist."""
        print("\n=== Testing Play Music by Artist ===")

        # Use artists that exist in the library and represent most edge cases
        artists = [
            {
                "artist": "Queen" # Previous searches were picking up 'Christine and the Queens"!
            },
            {
                "artist": "The Beatles"
            },
            {
                "artist": "Simon and Garfunkel" # Alexa hears and as 'and' but stored in plex as '&'
            },
            {
                "artist": "Belle and Sebastian" # Stored as 'and' in plex
            }
        ]

        for artist in artists:
            artist_name = artist["artist"]

            self.handler_input = create_mock_handler_input("PlayMusicByArtistIntent", {"artist": artist_name})
            self.playlist_manager = PlaylistManager(self.logger, self.handler_input)
            self.plex_connector = PlexConnector(self.logger, self.handler_input, self.playlist_manager)
            self.playback_controller = PlaybackController(self.logger, self.handler_input, self.playlist_manager)
            self.text_utils = TextUtils(self.logger, self.handler_input)
            self.plexapi_utils = PlexApiUtils(self.logger, self.text_utils)
            self.music_search = MusicSearch(
                self.logger,
                self.handler_input,
                self.playlist_manager,
                self.playback_controller,
                self.plex_connector,
                self.text_utils,
                self.plexapi_utils
            )

            # Set up localization data again for new handler_input
            self.handler_input.attributes_manager.request_attributes["_"] = {
                prompts.SKILL_INTENT_SLOTS_MISSING: "Please provide the required information.",
                prompts.PMS_CONNECTION_ERROR: "Unable to connect to Plex server.",
                prompts.PMS_SECTION_ERROR: "Error searching for section {}",
                prompts.PMS_SECTION_NOT_FOUND: "Music section not found.",
                prompts.PMS_CONNECTED: "Connection to Plex server successful.",
                prompts.PMS_TRACKS_SEARCH_EMPTY: "No tracks found.",
                prompts.PMS_ARTIST_SEARCH_ERROR: "Error searching for artist: {}",
                prompts.PMS_ARTIST_SEARCH_EMPTY: "Artist not found: {}",
                prompts.PMS_PLAYING: "Playing {}",
                prompts.PMS_PLNAME_MUSIC_BY_ARTIST: "Music by {}",
            }

            # Ensure connection before testing
            success, response = self.plex_connector.connect_plex()
            if not success:
                self.fail(f"Failed to connect to Plex server: {response}")

            # Patch get_slot_value_v2 to use our mock
            with patch('plextreme.music_search.get_slot_value_v2', side_effect=mock_get_slot_value_v2):
                response = self.music_search.play_music_by_artist()

            print(f"✓ Artist: {artist_name}")
            print(f"✓ Response: {response.output_speech if hasattr(response, 'output_speech') else 'N/A'}")

            playlist = self.handler_input.attributes_manager.persistent_attributes["playback_info"]["playlist"]
            print(f"✓ Playlist size: {len(playlist)}")

            if len(playlist) > 0:
                print(f"✓ First track: {list(playlist.values())[0]['title']}")

            self.assertIsNotNone(playlist, "Playlist should not be empty")
            self.assertGreaterEqual(len(playlist), 1, "Playlist should contain 1 or more song")

    def test_play_song_by_artist(self):
        """Test playing a specific song by an artist."""
        print("\n=== Testing Play Song by Artist ===")
        
        # Change these to a song/artist that exists in your library
        songs = [
            {
                "artist": "Gracie Abrams",
                "song": "I Love You, I'm Sorry"
            },
            {
                "artist": "The Beatles",
                "song": "Strawberry Fields Forever"
            },
            {
                "artist": "ABBA",
                "song": "Gimme Gimme Gimme"
            },
            {
                "artist": "ABBA",
                "song": "On and On and On"
            },
            {
                "artist": "The Automatic",
                "song": "Seriously i hate you guys"
            }
        ]

        for song in songs:

            self.handler_input = create_mock_handler_input("PlaySongByArtistIntent", {
                "artist": song["artist"],
                "song": song["song"]
            })
            self.playlist_manager = PlaylistManager(self.logger, self.handler_input)
            self.plex_connector = PlexConnector(self.logger, self.handler_input, self.playlist_manager)
            self.playback_controller = PlaybackController(self.logger, self.handler_input, self.playlist_manager)
            self.text_utils = TextUtils(self.logger, self.handler_input)
            self.plexapi_utils = PlexApiUtils(self.logger, self.text_utils)
            self.music_search = MusicSearch(
                self.logger,
                self.handler_input,
                self.playlist_manager,
                self.playback_controller,
                self.plex_connector,
                self.text_utils,
                self.plexapi_utils
            )

            # Set up localization data
            self.handler_input.attributes_manager.request_attributes["_"] = {
                prompts.SKILL_INTENT_SLOTS_MISSING: "Please provide the required information.",
                prompts.PMS_CONNECTION_ERROR: "Unable to connect to Plex server.",
                prompts.PMS_SECTION_ERROR: "Error searching for section {}",
                prompts.PMS_SECTION_NOT_FOUND: "Music section not found.",
                prompts.PMS_CONNECTED: "Connection to Plex server successful.",
                prompts.PMS_ARTIST_SEARCH_ERROR: "Error searching for artist: {}",
                prompts.PMS_ARTIST_SEARCH_EMPTY: "Artist not found: {}",
                prompts.PMS_SONG_SEARCH_ERROR: "Error searching for song: {song} by {artist}",
                prompts.PMS_PLAYING: "Playing {}",
                prompts.PMS_PLNAME_SONG: "{song} by {artist}",
            }

            # Ensure connection before testing
            success, response = self.plex_connector.connect_plex()
            if not success:
                self.fail(f"Failed to connect to Plex server: {response}")

            # Patch get_slot_value_v2 to use our mock
            with patch('plextreme.music_search.get_slot_value_v2', side_effect=mock_get_slot_value_v2):
                response = self.music_search.play_song_by_artist()

            print(f"✓ Song: {song['song']} by {song['artist']}")
            print(f"✓ Response: {response.output_speech if hasattr(response, 'output_speech') else 'N/A'}")

            playlist = self.handler_input.attributes_manager.persistent_attributes["playback_info"]["playlist"]
            print(f"✓ Playlist size: {len(playlist)}")

            self.assertIsNotNone(playlist, "Playlist should not be empty")
            self.assertEqual(len(playlist), 1, "Playlist should only contain 1 song")

    def test_play_music_by_genre(self):
        """Test playing music by genre."""
        print("\n=== Testing Play Music by Genre ===")
        
        # Change to a genre that exists in your library
        genres = [
            "Folk",
            "Electronic",
            "Reggae",
            "Pop/Rock"
        ]

        for genre_name in genres:

            self.handler_input = create_mock_handler_input("PlayMusicByGenreIntent", {"genre": genre_name})
            self.playlist_manager = PlaylistManager(self.logger, self.handler_input)
            self.plex_connector = PlexConnector(self.logger, self.handler_input, self.playlist_manager)
            self.playback_controller = PlaybackController(self.logger, self.handler_input, self.playlist_manager)
            self.text_utils = TextUtils(self.logger, self.handler_input)
            self.plexapi_utils = PlexApiUtils(self.logger, self.text_utils)
            self.music_search = MusicSearch(
                self.logger,
                self.handler_input,
                self.playlist_manager,
                self.playback_controller,
                self.plex_connector,
                self.text_utils,
                self.plexapi_utils
            )

            # Set up localization data
            self.handler_input.attributes_manager.request_attributes["_"] = {
                prompts.SKILL_INTENT_SLOTS_MISSING: "Please provide the required information.",
                prompts.PMS_CONNECTION_ERROR: "Unable to connect to Plex server.",
                prompts.PMS_SECTION_ERROR: "Error searching for section {}",
                prompts.PMS_SECTION_NOT_FOUND: "Music section not found.",
                prompts.PMS_CONNECTED: "Connection to Plex server successful.",
                prompts.PMS_TRACKS_SEARCH_EMPTY: "No tracks found.",
                prompts.PMS_GENRE_SEARCH_ERROR: "Error searching for genre: {}",
                prompts.PMS_GENRE_SEARCH_EMPTY: "No tracks found for genre: {}",
                prompts.PMS_PLAYING: "Playing {}",
                prompts.PMS_PLNAME_MUSIC_BY_GENRE: "{} genre music",
            }

            # Ensure connection before testing
            success, response = self.plex_connector.connect_plex()
            if not success:
                self.fail(f"Failed to connect to Plex server: {response}")

            # Patch get_slot_value_v2 to use our mock
            with patch('plextreme.music_search.get_slot_value_v2', side_effect=mock_get_slot_value_v2):
                response = self.music_search.play_music_by_genre()

            print(f"✓ Genre: {genre_name}")
            print(f"✓ Response: {response.output_speech if hasattr(response, 'output_speech') else 'N/A'}")

            playlist = self.handler_input.attributes_manager.persistent_attributes["playback_info"]["playlist"]
            print(f"✓ Playlist size: {len(playlist)}")

            self.assertIsNotNone(playlist, "Playlist should not be empty")
            self.assertGreaterEqual(len(playlist), 1, "Playlist should contain at least 1 song")

if __name__ == '__main__':
    unittest.main(verbosity=2)
