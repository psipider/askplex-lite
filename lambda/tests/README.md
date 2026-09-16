# Plextreme Lambda Test Suite

This test suite enables local testing of the Plextreme Lambda functions against your actual Plex server without deploying to AWS.

## Setup

1. **Install test dependencies:**
   ```bash
   cd lambda
   pip install -r requirements-test.txt
   ```

2. **Ensure your Plex configuration is correct in `plextreme/config.py`:**
   - `PMS_SERVER_TOKEN` - Your Plex token
   - `PMS_SERVER_NAME` - Your Plex server name
   - `PMS_DEFAULT_SECTION_NAME` - Your music library section name (default: "Music")

## Running Tests

### Run All Plex Connector Tests
```bash
cd lambda
python tests/test_plex_connector.py
```

### Run All Music Search Tests
```bash
cd lambda
python tests/test_music_search.py
```

### Run Specific Test Method
```bash
# Plex Connector tests
python tests/test_plex_connector.py TestPlexConnector.test_connect_to_plex
python tests/test_plex_connector.py TestPlexConnector.test_add_plex_track

# Music Search tests
python tests/test_music_search.py TestMusicSearch.test_play_random_music
python tests/test_music_search.py TestMusicSearch.test_play_music_by_artist
```

## Test Coverage

### TestPlexConnector (test_plex_connector.py)
- `test_connect_to_plex` - Tests connection to your Plex server
- `test_get_random_tracks` - Tests retrieving random tracks from your library
- `test_set_playlist_name` - Tests setting playlist name in persistent attributes
- `test_add_plex_track` - Tests adding a single Plex track to the playlist
- `test_add_plex_tracks` - Tests adding multiple Plex tracks to the playlist
- `test_connection_caching` - Tests that connection is cached when already connected

### TestMusicSearch (test_music_search.py)
- `test_play_random_music` - Tests the random music playback functionality
- `test_play_music_by_artist` - Tests searching and playing music by artist
- `test_play_song_by_artist` - Tests playing a specific song by an artist
- `test_play_music_by_genre` - Tests playing music by genre

## Customizing Tests

**Important:** The test suite uses placeholder artist, song, and genre names. You should modify these in `test_music_search.py` to match content in your Plex library:

### In `test_play_music_by_artist`:
```python
artist_name = "The Beatles"  # Change to an artist in your library
```

### In `test_play_song_by_artist`:
```python
artist_name = "The Beatles"  # Change to an artist in your library
song_name = "Hello"        # Change to a song in your library
```

### In `test_play_music_by_genre`:
```python
genre_name = "Rock"  # Change to a genre in your library
```

## Test Output

Tests will output detailed information including:
- ✓ Connection status
- ✓ Number of tracks retrieved
- ✓ Track details (title, artist)
- ✓ Playlist population status
- ✓ Response generation status

## Troubleshooting

### Connection Failures
- Verify your Plex token in `config.py` is valid
- Ensure your Plex server is accessible from your network
- Check that `PMS_SERVER_NAME` matches your actual server name

### Empty Results
- Verify the artist/song/genre names exist in your library
- Check that your music library section name is correct
- Ensure your library has content indexed

### Import Errors
- Ensure you're running tests from the `lambda` directory
- Verify all dependencies are installed: `pip install -r requirements.txt -r requirements-test.txt`

## Architecture

The test suite uses mock classes to simulate Alexa SDK components:
- `MockHandlerInput` - Simulates Alexa request handling
- `MockResponseBuilder` - Simulates response generation
- `MockAttributesManager` - Simulates attribute persistence
- `MockServiceClientFactory` - Simulates progressive response service

This allows you to test your business logic (Plex integration, playlist management, search functionality) without needing actual Alexa infrastructure.
