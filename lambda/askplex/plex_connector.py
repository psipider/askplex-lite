from typing import List, Dict, Optional, Tuple
from logging import Logger

from ask_sdk_model import Response

from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model.services.directive import (SendDirectiveRequest, SpeakDirective)

from plexapi.audio import Track
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound
from plexapi.myplex import MyPlexAccount
from plexapi.library import MusicSection

from . import config
from . import prompts
from .playlist_manager import PlaylistManager


class PlexConnector:
    """
    Manages Plex server connection and track addition operations.
    """

    _section: MusicSection = None

    def __init__(self, logger: Logger, handler_input: HandlerInput, playlist_manager: PlaylistManager) -> None:
        """
        Initializes the Plex connector with a logger, handler input, and playlist manager.
        Args:
            logger (Logger): The logger instance to be used for logging.
            handler_input (HandlerInput): The handler input instance.
            playlist_manager (PlaylistManager): The playlist manager instance.
        """
        self.logger = logger
        self.handler_input = handler_input
        self.playlist = playlist_manager

    def _create_plex_server(self) -> PlexServer:
        """
        Creates a PlexServer instance and establishes a connection to the server.
        Connection attempts are made in the following priority order:
        1. If the configuration (`config.PMS_USE_SERVER_URL`) is enabled, connect directly using the specified URL and token.
        2. If disabled, connect via MyPlexAccount and retrieve the target resource (server name).
        3. From the retrieved resource's connection list, search for an external HTTPS (plex.direct) URL and attempt connection.
        4. If the above fails or is not found, automatic fallback via `resource.connect()`.

        Returns:
            PlexServer: The PlexServer object with an established connection.

        Raises:
            Exception: Thrown when no valid connection destination is found, authentication to MyPlex fails,
                       or all connection attempts timeout.
        """
        if config.PMS_USE_SERVER_URL:
            return PlexServer(config.PMS_SERVER_URL, config.PMS_SERVER_TOKEN)
        plex_server = None
        account = MyPlexAccount(token=config.PMS_SERVER_TOKEN)
        resource = account.resource(config.PMS_SERVER_NAME)
        target_url = next((c.uri for c in resource.connections if not c.local and c.uri.startswith('https') and "plex.direct" in c.uri), None)
        if target_url:
            try:
                self.logger.debug(f"Attempting direct URL connection: {target_url}")
                plex_server = PlexServer(target_url, config.PMS_SERVER_TOKEN, timeout=3)
            except Exception as exception:
                self.logger.warning(f"Direct URL connection failed: {exception}. Falling back to resource.connect()")
        if plex_server is None:
            plex_server = resource.connect(timeout=3)
        return plex_server

    def connect_plex(self) -> Tuple[bool, Optional[Response]]:
        """
        Establishes a connection to the Plex server and the specified library section.
        If already connected (cached), the connection process is skipped and success is returned.
        If not connected, connects to the server based on configuration and caches the target section (Music, etc.) in the class variable `_section`.

        Returns:
            Tuple[bool, Optional[Response]]: 
                - bool: True on connection success, False on failure.
                - Response: Response object to convey errors to the user on failure.
                           None on success.

        Raises:
            NotFound: When the specified section name does not exist in the server.
            Exception: Connection errors such as authentication failure, timeout, or network unreachability.
        """
        self.logger.debug('In connect_plex()')

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        if PlexConnector._section is not None:
            self.logger.debug('Already connected.')
            return True, None

        self.logger.info(f"Connecting to section: {config.PMS_DEFAULT_SECTION_NAME}")

        try:
            plex_server = self._create_plex_server()
            section = plex_server.library.section(config.PMS_DEFAULT_SECTION_NAME)
            PlexConnector._section = section
            self.logger.info('Successfully connected to section.')
            self.send_progressive_response(self.handler_input, data[prompts.PMS_CONNECTED])
            return True, None
        except NotFound as exception:
            self.logger.error(f"Plex section not found: {exception}")
            speak_output = data[prompts.PMS_SECTION_NOT_FOUND]
        except Exception as exception:
            self.logger.error(f"Plex connection error: {exception}")
            speak_output = data[prompts.PMS_CONNECTION_ERROR]
        return False, self._build_speak_ask_response(speak_output)

    def set_playlist_name(self, name: str) -> None:
        """
        Sets the playlist name in the persistent attributes.

        Args:
            name (str): The name of the playlist to be set.

        Returns:
            None
        """
        self.logger.debug('In set_playlist_name()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")
        playback_info["playlist_name"] = name

    def add_plex_track(self, plex_track: Track, playback_info: Dict = None) -> None:
        """
        Adds a Plex track to the playlist.
        Args:
            plex_track (Track): The Plex track to be added. It should be an instance of the Track class.
            playback_info (Dict, optional): Playback info. The default value is None. If omitted, it will be retrieved from "handler_input.attributes_manager.persistent_attributes".
        Returns:
            None
        """
        self.logger.debug('In add_plex_track()')

        if playback_info is None:
            persistence_attr = self.handler_input.attributes_manager.persistent_attributes
            playback_info = persistence_attr.get("playback_info")

        track = {
                "id": str(plex_track.ratingKey),
                "title": plex_track.title,
                "artist": plex_track.grandparentTitle,
                "album": plex_track.parentTitle,
                }

        self.playlist.add_track(track, playback_info)

    def add_plex_tracks(self, plex_track_list: List[Track]) -> None:
        """
        Adds a list of Plex tracks to the playlist.
        Args:
            plex_track_list (List[Track]): A list of Plex track objects to be added.
        Returns:
            None
        """
        self.logger.debug('In add_plex_tracks()')

        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")
        for plex_track in plex_track_list:
            self.add_plex_track(plex_track, playback_info)

    def _build_speak_ask_response(self, speak_output) -> Response:
        """
        Generates a response object to notify the user of an error and prompt for retry.

        Args:
            speak_output (str): The content of the error message to be spoken to the user.

        Returns:
            Response: An Alexa SDK Response object with speak and ask properties set.
                      This opens the microphone after audio output to wait for the user's response.
        """
        return (
            self.handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )

    def send_progressive_response(self, handler_input: HandlerInput, speech_text: str) -> None:
        """
        Sends an immediate voice response using ask_sdk_core to reset
        Alexa's internal 8-second timeout window.
        """
        try:
            self.logger.debug('In send_progressive_response()')
            # 1. Pull the unique Request ID from the incoming envelope
            request_id = handler_input.request_envelope.request.request_id

            # 2. Get the active directive client from the service factory
            directive_client = handler_input.service_client_factory.get_directive_service()

            # 3. Construct the voice directive payload
            self.logger.debug('Sending progressive response: ' + speech_text)
            directive_request = SendDirectiveRequest(
                header={"requestId": request_id},
                directive=SpeakDirective(speech=speech_text)
            )

            # 4. Fire the message out to the active device instantly
            directive_client.enqueue(directive_request)

        except Exception as e:
            # Using a universal catch prevents missing SDK components from breaking the code.
            # If it fails, the script seamlessly rolls right into your Plex processing.
            # Note: Cannot access logger here as it's a standalone function
            self.logger.error(f"Progressive response skipped/failed: {str(e)}")
            pass