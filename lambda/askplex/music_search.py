from typing import Optional
from logging import Logger

from ask_sdk_model import Response

from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import get_slot_value_v2

from . import config
from . import prompts
from . import plexapi_utils
from .playlist_manager import PlaylistManager
from .playback_controller import PlaybackController
from .plex_connector import PlexConnector
from .text_utils import TextUtils


class MusicSearch:
    """
    Manages music search and playback operations including random music, artist-based search, 
    song/album/genre search, and playlist playback.
    """

    def __init__(self, logger: Logger, handler_input: HandlerInput, playlist_manager: PlaylistManager, 
                 playback_controller: PlaybackController, plex_connector: PlexConnector, text_utils: TextUtils) -> None:
        """
        Initializes the music search handler with logger, handler input, and required managers.
        Args:
            logger (Logger): The logger instance to be used for logging.
            handler_input (HandlerInput): The handler input instance.
            playlist_manager (PlaylistManager): The playlist manager instance.
            playback_controller (PlaybackController): The playback controller instance.
            plex_connector (PlexConnector): The Plex connector instance.
            text_utils (TextUtils): The text utilities instance.
        """
        self.logger = logger
        self.handler_input = handler_input
        self.playlist = playlist_manager
        self.playback = playback_controller
        self.plex = plex_connector
        self.text = text_utils

    def play_random_music(self) -> Response:
        """
        Plays a random selection of music tracks.
        This method searches for random tracks. If no tracks are found or an error
        occurs during the search, an appropriate response is returned. Otherwise,
        it clears the current playlist, adds the found tracks to the playlist, sets
        the playlist name, and starts playback.
        Returns:
            Response: The response object containing the result of the playback action.
        """
        self.logger.debug('In play_random_music()')

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        # Search for random tracks
        try:
            plex_track_list = plexapi_utils.get_random_tracks(PlexConnector._section, config.PMS_DEFAULT_MAX_RESULTS)
        except Exception as exception:
            speak_output = data[prompts.PMS_CONNECTION_ERROR]
            self.logger.error(exception)
            return self.plex._build_speak_ask_response(speak_output)

        if len(plex_track_list) == 0:
            speak_output = data[prompts.PMS_TRACKS_SEARCH_EMPTY]
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        self.playlist.clear_playlist()
        self.plex.add_plex_tracks(plex_track_list)

        playlist_name = data[prompts.PMS_PLNAME_RANDOM_MUSIC]
        self.plex.set_playlist_name(playlist_name)
        speak_output = data[prompts.PMS_PLAYING].format(playlist_name)

        self.handler_input.response_builder.speak(speak_output)
        self.logger.info(speak_output)

        return self.playback.start_playback(PlexConnector._section)

    def play_music_by_artist(self) -> Response:
        """
        Plays a music selection by a specified artist.
        This method searches for music by the specified artist, sorted by popularity
        if available in the plex media server. If no tracks are found or an error
        occurs during the search, an appropriate response is returned. Otherwise,
        it clears the current playlist, adds the found tracks to the playlist, sets
        the playlist name, and starts playback.
        Returns:
            Response: The response object containing the result of the playback action.
        """
        self.logger.debug('In play_music_by_artist()')

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        # Get variable(s) from intent
        artist = get_slot_value_v2(self.handler_input, 'artist')
        if artist is None:
            speak_output = data[prompts.SKILL_INTENT_SLOTS_MISSING]
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)
        
        artist_query = self.text._normalize(artist.value)

        # Search for the artist
        try:
            artist_result = plexapi_utils.get_artist(PlexConnector._section, artist_query)
        except Exception as exception:
            speak_output = data[prompts.PMS_ARTIST_SEARCH_ERROR].format(artist_query)
            self.logger.error(exception)
            return self.plex._build_speak_ask_response(speak_output)

        if artist_result is None:
            speak_output = data[prompts.PMS_ARTIST_SEARCH_EMPTY].format(artist_query)
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        # Get a list the popular tracks by the artist
        plex_track_list = artist_result.popularTracks()
        if len(plex_track_list) == 0:
            # No popular tracks, so look for any tracks
            plex_track_list = plexapi_utils.get_random_tracks_by_artist(PlexConnector._section, config.PMS_DEFAULT_MAX_RESULTS, artist_result)
            if len(plex_track_list) == 0:
                speak_output = data[prompts.PMS_TRACKS_SEARCH_EMPTY]
                return self.plex._build_speak_ask_response(speak_output)


        self.playlist.clear_playlist()
        self.plex.add_plex_tracks(plex_track_list)

        playlist_name = data[prompts.PMS_PLNAME_MUSIC_BY_ARTIST].format(artist.value)
        self.plex.set_playlist_name(playlist_name)
        speak_output = data[prompts.PMS_PLAYING].format(playlist_name)

        self.handler_input.response_builder.speak(speak_output)
        self.logger.info(speak_output)
        return self.playback.start_playback(PlexConnector._section)

    def play_song_by_artist(self) -> Response:
        """
        Play a specific song by a given artist.
        This method searches the specific song. If no track is found or an error
        occurs during the search, an appropriate response is returned. Otherwise,
        it clears the current playlist, adds the found tracks to the playlist, sets
        the playlist name, and starts playback.
        Returns:
            Response: The response object containing the result of the playback action.
        """
        self.logger.debug('In play_song_by_artist()')

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        # Get variable(s) from intent
        artist = get_slot_value_v2(self.handler_input, 'artist')
        song = get_slot_value_v2(self.handler_input, 'song')
        if artist is None or song is None:
            speak_output = data[prompts.SKILL_INTENT_SLOTS_MISSING]
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        artist_query = self.text._normalize(artist.value)
        song_query = self.text._normalize(song.value)

        # Search for the artist
        try:
            artist_result = plexapi_utils.get_artist(PlexConnector._section, artist_query)
        except Exception as exception:
            speak_output = data[prompts.PMS_ARTIST_SEARCH_ERROR].format(artist_query)
            self.logger.error(exception)
            return self.plex._build_speak_ask_response(speak_output)

        if artist_result is None:
            speak_output = data[prompts.PMS_ARTIST_SEARCH_EMPTY].format(artist_query)
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        # Search for the song
        try:
            plex_track = plexapi_utils.get_track(artist_result, song_query)
        except Exception as exception:
            speak_output = data[prompts.PMS_SONG_SEARCH_ERROR].format(song=song_query, artist=artist_query)
            self.logger.error(exception)
            return self.plex._build_speak_ask_response(speak_output)

        if plex_track is None:
            speak_output = data[prompts.PMS_SONG_SEARCH_ERROR].format(song=song_query, artist=artist_query)
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        self.playlist.clear_playlist()
        self.plex.add_plex_track(plex_track)

        playlist_name = data[prompts.PMS_PLNAME_SONG].format(song=song_query, artist=artist_query)
        self.plex.set_playlist_name(playlist_name)
        speak_output = data[prompts.PMS_PLAYING].format(playlist_name)

        self.handler_input.response_builder.speak(speak_output)
        self.logger.info(speak_output)
        return self.playback.start_playback(PlexConnector._section)

    def play_album_by_artist(self) -> Response:
        """
        Play a specific album by a given artist.
        This method searches the specific album. If no tracks are found or an error
        occurs during the search, an appropriate response is returned. Otherwise,
        it clears the current playlist, adds the found tracks to the playlist, sets
        the playlist name, and starts playback.
        Returns:
            Response: The response object containing the result of the playback action.
        """
        self.logger.debug('In play_album_by_artist()')

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        # Get variable(s) from intent
        artist = get_slot_value_v2(self.handler_input, 'artist')
        album = get_slot_value_v2(self.handler_input, 'album')
        if artist is None or album is None:
            speak_output = data[prompts.SKILL_INTENT_SLOTS_MISSING]
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        artist_query = self.text._normalize(artist.value)
        album_query = self.text._normalize(album.value)

        # Search for the artist
        try:
            artist_result = plexapi_utils.get_artist(PlexConnector._section, artist_query)
        except Exception as exception:
            speak_output = data[prompts.PMS_ARTIST_SEARCH_ERROR].format(artist_query)
            self.logger.error(exception)
            return self.plex._build_speak_ask_response(speak_output)

        if artist_result is None:
            speak_output = data[prompts.PMS_ARTIST_SEARCH_EMPTY].format(artist_query)
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        # Search for the album
        try:
            plex_track_list = plexapi_utils.get_album(artist_result, album_query)
        except Exception as exception:
            speak_output = data[prompts.PMS_ALBUM_SEARCH_ERROR].format(album_query, artist=artist_query)
            self.logger.error(exception)
            return self.plex._build_speak_ask_response(speak_output)

        if plex_track_list is None:
            speak_output = data[prompts.PMS_ALBUM_SEARCH_EMPTY].format(album=album_query, artist=artist_query)
            self.logger.error("Unable to locate requested album - Artist: {artist_result}, Album: {album_query}")
            return self.plex._build_speak_ask_response(speak_output)

        self.playlist.clear_playlist()
        self.plex.add_plex_tracks(plex_track_list)

        playlist_name = data[prompts.PMS_PLNAME_ALBUM].format(album=album_query, artist=artist_query)
        self.plex.set_playlist_name(playlist_name)
        speak_output = data[prompts.PMS_PLAYING].format(playlist_name)

        self.handler_input.response_builder.speak(speak_output)
        self.logger.info(speak_output)
        return self.playback.start_playback(PlexConnector._section)

    def play_music_by_genre(self) -> Response:
        """
        Play music by a given genre.
        This method searches music by genre. If no tracks are found or an error
        occurs during the search, an appropriate response is returned. Otherwise,
        it clears the current playlist, adds the found tracks to the playlist, sets
        the playlist name, and starts playback.
        Returns:
            Response: The response object containing the result of the playback action.
        """
        self.logger.debug('In play_music_by_genre()')

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        # Get variable(s) from intent
        genre = get_slot_value_v2(self.handler_input, 'genre')
        if genre is None:
            speak_output = data[prompts.SKILL_INTENT_SLOTS_MISSING]
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        genre_query = self.text._normalize(genre.value)

        # Search for the style (Plex server is more specfic with style than genre tags)
        try:
            plex_track_list = plexapi_utils.get_random_tracks_by_genre(PlexConnector._section, config.PMS_DEFAULT_MAX_RESULTS, genre_query)
        except Exception as exception:
            speak_output = data[prompts.PMS_GENRE_SEARCH_ERROR].format(genre_query)
            self.logger.error(exception)
            return self.plex._build_speak_ask_response(speak_output)

        if len(plex_track_list)==0:
            speak_output = data[prompts.PMS_GENRE_SEARCH_EMPTY].format(genre_query)
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        self.playlist.clear_playlist()
        self.plex.add_plex_tracks(plex_track_list)

        playlist_name = data[prompts.PMS_PLNAME_MUSIC_BY_GENRE].format(genre_query)
        self.plex.set_playlist_name(playlist_name)
        speak_output = data[prompts.PMS_PLAYING].format(playlist_name)

        self.handler_input.response_builder.speak(speak_output)
        self.logger.info(speak_output)
        return self.playback.start_playback(PlexConnector._section)

    def play_playlist(self) -> Response:
        """
        Play a plex playlist.
        This method searches for a specific playlist. If no playlist is found or an error
        occurs during the search, an appropriate response is returned. Otherwise,
        it clears the current playlist, adds the found tracks to the playlist, sets
        the playlist name, and starts playback.
        Returns:
            Response: The response object containing the result of the playback action.
        """
        self.logger.debug('In play_playlist()')

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        # Get variable(s) from intent
        playlist = get_slot_value_v2(self.handler_input, 'playlist')
        if playlist is None:
            speak_output = data[prompts.SKILL_INTENT_SLOTS_MISSING]
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        playlist_query = self.text._normalize(playlist.value)

        # Search for the playlist
        try:
            plex_track_list = plexapi_utils.get_playlist(PlexConnector._section._server, playlist_query)
        except Exception as exception:
            speak_output = data[prompts.PMS_PLAYLIST_SEARCH_ERROR].format(playlist_query)
            self.logger.error(exception)
            return self.plex._build_speak_ask_response(speak_output)

        if plex_track_list is None:
            speak_output = data[prompts.PMS_PLAYLIST_SEARCH_EMPTY].format(playlist_query)
            self.logger.error(speak_output)
            return self.plex._build_speak_ask_response(speak_output)

        self.playlist.clear_playlist()
        self.plex.add_plex_tracks(plex_track_list)
        
        play_mode = get_slot_value_v2(self.handler_input, 'mode')
        if play_mode is not None:
            self.logger.debug('Mode set to: ' + play_mode.value)
            play_mode = self.text._normalize(play_mode.value)
            if play_mode == 'shuffle':
                self.playlist.shuffle_play_order(True)
                self.logger.info('Shuffle mode set')

        playlist_name = data[prompts.PMS_PLNAME_PLAYLIST].format(playlist_query)
        self.plex.set_playlist_name(playlist_name)
        speak_output = data[prompts.PMS_PLAYING].format(playlist_name)

        self.handler_input.response_builder.speak(speak_output)
        self.logger.info(speak_output)
        return self.playback.start_playback(PlexConnector._section)
