"""
Test suite for PlexConnector class.
Tests against actual Plex server for local development and optimization.
"""
import sys
import os
import logging
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plextreme import config
from plextreme import prompts
from plextreme.plex_connector import PlexConnector
from plextreme.playlist_manager import PlaylistManager
from plextreme.plexapi_utils import PlexApiUtils
from tests.mocks.alexa_mocks import create_mock_handler_input


class TestPlexConnector(unittest.TestCase):
    """Test cases for PlexConnector class."""
    
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
        self.plexapi = PlexApiUtils(self.logger)
        
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
    
    def test_connect_to_plex(self):
        """Test connection to Plex server."""
        print("\n=== Testing Plex Connection ===")
        success, response = self.plex_connector.connect_plex()
        
        if success:
            print("✓ Successfully connected to Plex server")
            print(f"✓ Section: {PlexConnector._section.title}")
            print(f"✓ Total tracks: {PlexConnector._section.totalSize}")
        else:
            print(f"✗ Failed to connect: {response}")
        
        self.assertTrue(success, "Should successfully connect to Plex server")
        self.assertIsNotNone(PlexConnector._section, "Section should be set after connection")
    
    def test_get_random_tracks(self):
        """Test retrieving random tracks from Plex."""
        print("\n=== Testing Random Track Retrieval ===")
        
        # Ensure connection
        success, response = self.plex_connector.connect_plex()
        if not success:
            self.fail(f"Failed to connect to Plex server: {response}")
        
        self.assertIsNotNone(PlexConnector._section, "Section should be set after connection")
        
        tracks = self.plexapi.get_random_tracks(PlexConnector._section, config.PMS_DEFAULT_MAX_RESULTS)
        
        print(f"✓ Retrieved {len(tracks)} random tracks")
        if len(tracks) > 0:
            print(f"✓ First track: {tracks[0].title} by {tracks[0].grandparentTitle}")
        
        self.assertGreater(len(tracks), 0, "Should retrieve at least one track")
    
    def test_set_playlist_name(self):
        """Test setting playlist name in persistent attributes."""
        print("\n=== Testing Set Playlist Name ===")
        
        test_name = "Test Playlist"
        self.plex_connector.set_playlist_name(test_name)
        
        playlist_name = self.handler_input.attributes_manager.persistent_attributes["playback_info"]["playlist_name"]
        self.assertEqual(playlist_name, test_name, "Playlist name should be set correctly")
        print(f"✓ Playlist name set to: {playlist_name}")
    
    def test_add_plex_track(self):
        """Test adding a single Plex track to the playlist."""
        print("\n=== Testing Add Plex Track ===")
        
        # Ensure connection
        success, response = self.plex_connector.connect_plex()
        if not success:
            self.fail(f"Failed to connect to Plex server: {response}")
        
        # Get a random track to add
        tracks = self.plexapi.get_random_tracks(PlexConnector._section, 1)
        
        if len(tracks) == 0:
            self.skipTest("No tracks available to test")
        
        test_track = tracks[0]
        self.plex_connector.add_plex_track(test_track)
        
        playlist = self.handler_input.attributes_manager.persistent_attributes["playback_info"]["playlist"]
        self.assertEqual(len(playlist), 1, "Playlist should contain one track")
        
        track_id = list(playlist.values())[0]["id"]
        self.assertEqual(track_id, str(test_track.ratingKey), "Track ID should match")
        print(f"✓ Added track: {test_track.title} by {test_track.grandparentTitle}")
    
    def test_add_plex_tracks(self):
        """Test adding multiple Plex tracks to the playlist."""
        print("\n=== Testing Add Plex Tracks ===")
        
        # Ensure connection
        success, response = self.plex_connector.connect_plex()
        if not success:
            self.fail(f"Failed to connect to Plex server: {response}")
        
        # Get random tracks to add
        tracks = self.plexapi.get_random_tracks(PlexConnector._section, 5)
        
        if len(tracks) == 0:
            self.skipTest("No tracks available to test")
        
        self.plex_connector.add_plex_tracks(tracks)
        
        playlist = self.handler_input.attributes_manager.persistent_attributes["playback_info"]["playlist"]
        self.assertEqual(len(playlist), len(tracks), f"Playlist should contain {len(tracks)} tracks")
        print(f"✓ Added {len(tracks)} tracks to playlist")
    
    def test_connection_caching(self):
        """Test that connection is cached when already connected."""
        print("\n=== Testing Connection Caching ===")
        
        # First connection
        success1, response1 = self.plex_connector.connect_plex()
        self.assertTrue(success1, "First connection should succeed")
        
        # Store the section reference
        section1 = PlexConnector._section
        
        # Second connection should use cache
        success2, response2 = self.plex_connector.connect_plex()
        self.assertTrue(success2, "Second connection should succeed")
        self.assertIsNone(response2, "Second connection should return None (cached)")
        
        # Section should be the same object
        section2 = PlexConnector._section
        self.assertIs(section1, section2, "Section should be the same cached object")
        print("✓ Connection caching works correctly")


if __name__ == '__main__':
    unittest.main(verbosity=2)
