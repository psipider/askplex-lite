from typing import Dict
from logging import Logger

from ask_sdk_model import Response
from ask_sdk_model.interfaces.audioplayer import AudioItem, Stream, AudioItemMetadata, PlayDirective, PlayBehavior, StopDirective
from ask_sdk_model.interfaces import display

from ask_sdk_core.handler_input import HandlerInput

from .playlist_manager import PlaylistManager


class PlaybackController:
    """
    Manages playback control operations including play, pause, next, previous, and track conversion.
    """

    def __init__(self, logger: Logger, handler_input: HandlerInput, playlist_manager: PlaylistManager) -> None:
        """
        Initializes the playback controller with a logger, handler input, and playlist manager.
        Args:
            logger (Logger): The logger instance to be used for logging.
            handler_input (HandlerInput): The handler input instance.
            playlist_manager (PlaylistManager): The playlist manager instance.
        """
        self.logger = logger
        self.handler_input = handler_input
        self.playlist = playlist_manager

    def track_to_audio_item(self, track: Dict, offset: int, previous_token: str, section) -> AudioItem:
        """
        Converts a track (Dict) to an AudioItem object.
        Args:
            track (Dict): A dictionary containing track information with keys "title", "artist", "album", "album_art", "artist_art", "id", and "uri".
            offset (int): The offset in milliseconds for the audio stream.
            previous_token (str): The expected previous token for the audio stream.
            section: The Plex music section.
        Returns:
            AudioItem: An object containing the audio stream and metadata for the track.
        """
        self.logger.debug('In track_to_audio_item()')

        id = track["id"]
        plex_track = section.fetchItem(int(id))
        metadata = AudioItemMetadata(
            title = track["title"],
            subtitle = track["artist"]
        )
        album_art = plex_track.url(plex_track.parentThumb)
        if album_art is not None:
            metadata.art=display.Image(
                content_description = track["album"],
                sources=[
                    display.ImageInstance(
                        url=album_art
                    )
                ]
            )
        artist_art = plex_track.url(plex_track.grandparentArt)
        if artist_art is not None:
            metadata.background_image=display.Image(
                content_description = track["artist"],
                sources=[
                    display.ImageInstance(
                        url=artist_art
                    )
                ]
            )
        url = plex_track.getStreamURL().replace("m3u8", "mp3")

        stream = Stream(token=id, url=url, offset_in_milliseconds=offset, expected_previous_token=previous_token)
        return AudioItem(stream=stream, metadata=metadata)

    def resume_playback(self, section) -> Response:
        """
        Handles the resume command.
        This method resumes playback with the saved offset.
        Returns:
            Response: The response object with the play directive and the current track
            in audio item format. If there is no current track, the response object is empty.
        """
        self.logger.debug('In resume_playback()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")

        current_track = self.playlist.get_current_track()

        playback_info['next_stream_enqueued'] = False

        directive = PlayDirective(play_behavior=PlayBehavior.REPLACE_ALL, audio_item=self.track_to_audio_item(current_track, int(playback_info["offset_in_ms"]), None, section))
        self.handler_input.response_builder.add_directive(directive).set_should_end_session(True)

        return self.handler_input.response_builder.response

    def start_playback(self, section) -> Response:
        """
        Handles the start over command.
        This method resets the offset of the current track and then resumes playback.
        Returns:
            Response: The response object with the play directive and the current track
            in audio item format. If there is no current track, the response object is empty.
        """
        self.logger.debug('In start_playback()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")

        playback_info["offset_in_ms"] = 0

        return self.resume_playback(section)

    def pause_playback(self) -> Response:
        """
        Handles the pause command.
        Returns:
            Response: The response object with the stop directive.
        """
        self.logger.debug('In pause_playback()')

        self.handler_input.response_builder.add_directive(StopDirective()).set_should_end_session(True)
        return self.handler_input.response_builder.response

    def previous_playback(self, section) -> Response:
        """
        Handles the previous track command.
        Returns:
            Response: The response object with the play directive and the previous track
            in audio item format. If there are no more tracks, the response object is empty.
        """
        self.logger.debug('In previous_playback()')

        prevous_track = self.playlist.get_previous_track()
        if prevous_track == None:
            return self.handler_input.response_builder.response

        directive = PlayDirective(play_behavior=PlayBehavior.REPLACE_ALL, audio_item=self.track_to_audio_item(prevous_track, 0, None, section))
        self.handler_input.response_builder.add_directive(directive).set_should_end_session(True)

        return self.handler_input.response_builder.response

    def next_playback(self, section) -> Response:
        """
        Handles the next track command.
        Returns:
            Response: The response object with the play directive and the next track
            in audio item format. If there are no more tracks, the response object is empty.
        """
        self.logger.debug('In next_playback()')

        next_track = self.playlist.get_next_track(True)
        if next_track == None:
            return self.handler_input.response_builder.response

        self.logger.debug(f'next_track: {next_track["title"]} by {next_track["artist"]}')

        directive = PlayDirective(play_behavior=PlayBehavior.REPLACE_ALL, audio_item=self.track_to_audio_item(next_track, 0, None, section))
        self.handler_input.response_builder.add_directive(directive).set_should_end_session(True)

        return self.handler_input.response_builder.response

    def loop_playback(self, enable: bool) -> Response:
        """
        Toggles playlist loop.
        Args:
            enable (bool): If True, enables the loop. If False, disables it.
        Returns:
            Response: The response object with no output speech.
        """
        self.logger.debug('In loop_playback()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_setting = persistence_attr.get("playback_setting")

        playback_setting["loop"] = enable

        return self.handler_input.response_builder.response

    def shuffle_playback(self, enable: bool) -> Response:
        """
        Toggles shuffle playback mode.
        Args:
            enable (bool): If True, shuffles the playlist. If False, re-sorts it.
        Returns:
            Response: The response object with no output speech.
        """
        self.logger.debug('In shuffle_playback()')

        self.playlist.shuffle_play_order(enable)

        return self.handler_input.response_builder.response

    def retrieve_track_details(self) -> Response:
        """
        Retrieves the details of the current track.
        Returns:
            Response: The response object containing the spoken output with the track details.
        """
        self.logger.debug('In retrieve_track_details()')

        from . import prompts

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        # Get the current track
        current_track = self.playlist.get_current_track()

        # Ignore the request if there is no track
        if current_track == None:
            return self.handler_input.response_builder.response

        speak_output = data[prompts.SKILL_SONG_DETAILS].format(song=current_track["title"], artist=current_track["artist"])
        self.logger.info(speak_output)

        self.handler_input.response_builder.speak(speak_output).set_should_end_session(True)
        return self.handler_input.response_builder.response
