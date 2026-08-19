from typing import Optional, Tuple, Dict, List
from logging import Logger

from ask_sdk_model import Response

from ask_sdk_core.handler_input import HandlerInput

from .playlist_manager import PlaylistManager
from .playback_controller import PlaybackController
from .playback_events import PlaybackEvents
from .plex_connector import PlexConnector
from .music_search import MusicSearch
from .text_utils import TextUtils

from plexapi.audio import Track


class Controller:
    """
    Controller class for managing playlist and playback operations.
    This class acts as a facade, delegating operations to specialized manager classes.
    """

    _section = None

    def __init__(self, logger: Logger, handler_input: HandlerInput) -> None:
        """
        Initializes the controller with a logger and the handler input instance.
        Args:
            logger (Logger): The logger instance to be used for logging.
            handler_input (HandlerInput): The handler input instance.
        """
        self.logger = logger
        self.handler_input = handler_input

        # Initialize manager components
        self.playlist_manager = PlaylistManager(logger, handler_input)
        self.playback_controller = PlaybackController(logger, handler_input, self.playlist_manager)
        self.playback_events = PlaybackEvents(logger, handler_input, self.playlist_manager, self.playback_controller)
        self.plex_connector = PlexConnector(logger, handler_input, self.playlist_manager)
        self.text_utils = TextUtils(logger, handler_input)
        self.music_search = MusicSearch(logger, handler_input, self.playlist_manager, self.playback_controller, self.plex_connector, self.text_utils)

    # Playlist methods - delegated to PlaylistManager
    def add_track(self, track: Dict, playback_info: Dict) -> None:
        return self.playlist_manager.add_track(track, playback_info)

    def get_next_track(self, update_index: bool) -> Dict:
        return self.playlist_manager.get_next_track(update_index)

    def get_previous_track(self) -> Dict:
        return self.playlist_manager.get_previous_track()

    def get_current_track(self) -> Dict:
        return self.playlist_manager.get_current_track()

    def shuffle_play_order(self, shuffle: bool) -> None:
        return self.playlist_manager.shuffle_play_order(shuffle)

    def clear_playlist(self) -> None:
        return self.playlist_manager.clear_playlist()

    # Playback control methods - delegated to PlaybackController
    def track_to_audio_item(self, track: Dict, offset: int, previous_token: str):
        return self.playback_controller.track_to_audio_item(track, offset, previous_token, PlexConnector._section)

    def resume_playback(self) -> Response:
        return self.playback_controller.resume_playback(PlexConnector._section)

    def start_playback(self) -> Response:
        return self.playback_controller.start_playback(PlexConnector._section)

    def pause_playback(self) -> Response:
        return self.playback_controller.pause_playback()

    def previous_playback(self) -> Response:
        return self.playback_controller.previous_playback(PlexConnector._section)

    def next_playback(self) -> Response:
        return self.playback_controller.next_playback(PlexConnector._section)

    def loop_playback(self, enable: bool) -> Response:
        return self.playback_controller.loop_playback(enable)

    def shuffle_playback(self, enable: bool) -> Response:
        return self.playback_controller.shuffle_playback(enable)

    def retrieve_track_details(self) -> Response:
        return self.playback_controller.retrieve_track_details()

    # Playback event methods - delegated to PlaybackEvents
    def playback_started(self) -> Response:
        return self.playback_events.playback_started()

    def playback_stopped(self) -> Response:
        return self.playback_events.playback_stopped()

    def playback_nearly_finished(self) -> Response:
        return self.playback_events.playback_nearly_finished(PlexConnector._section)

    def playback_finished(self) -> Response:
        return self.playback_events.playback_finished()

    def playback_failed(self) -> Response:
        return self.playback_events.playback_failed(PlexConnector._section)

    # Plex connection methods - delegated to PlexConnector
    def connect_plex(self) -> Tuple[bool, Optional[Response]]:
        return self.plex_connector.connect_plex()

    def set_playlist_name(self, name: str) -> None:
        return self.plex_connector.set_playlist_name(name)

    def add_plex_track(self, plex_track: Track, playback_info: Dict = None) -> None:
        return self.plex_connector.add_plex_track(plex_track, playback_info)

    def add_plex_tracks(self, plex_track_list: List[Track]) -> None:
        return self.plex_connector.add_plex_tracks(plex_track_list)

    # Music search methods - delegated to MusicSearch
    def play_random_music(self) -> Response:
        return self.music_search.play_random_music()

    def play_music_by_artist(self) -> Response:
        return self.music_search.play_music_by_artist()

    def play_song_by_artist(self) -> Response:
        return self.music_search.play_song_by_artist()

    def play_album_by_artist(self) -> Response:
        return self.music_search.play_album_by_artist()

    def play_music_by_genre(self) -> Response:
        return self.music_search.play_music_by_genre()

    def play_playlist(self) -> Response:
        return self.music_search.play_playlist()

    # Text utility methods - delegated to TextUtils
    def _normalize(self, source: str) -> str:
        return self.text_utils._normalize(source)

    def _convert_kanji_to_int(self, source) -> str:
        return self.text_utils._convert_kanji_to_int(source)

    # ASK SDK utility method - delegated to PlexConnector
    def _build_speak_ask_response(self, speak_output) -> Response:
        return self.plex_connector._build_speak_ask_response(speak_output)
