from typing import Dict
from logging import Logger

from ask_sdk_model import Response

from ask_sdk_core.handler_input import HandlerInput

from .playlist_manager import PlaylistManager
from .playback_controller import PlaybackController


class PlaybackEvents:
    """
    Manages playback event handlers including started, stopped, nearly finished, finished, and failed events.
    """

    def __init__(self, logger: Logger, handler_input: HandlerInput, playlist_manager: PlaylistManager, playback_controller: PlaybackController) -> None:
        """
        Initializes the playback events handler with a logger, handler input, playlist manager, and playback controller.
        Args:
            logger (Logger): The logger instance to be used for logging.
            handler_input (HandlerInput): The handler input instance.
            playlist_manager (PlaylistManager): The playlist manager instance.
            playback_controller (PlaybackController): The playback controller instance.
        """
        self.logger = logger
        self.handler_input = handler_input
        self.playlist = playlist_manager
        self.playback = playback_controller

    def playback_started(self) -> Response:
        """
        Handles the event when playback is started.
        This method only sets the playback session and returns the response.
        Returns:
            Response: The response object with no output speech.
        """
        self.logger.debug('In playback_started()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")

        playback_info["in_playback_session"] = True

        return self.handler_input.response_builder.response

    def playback_stopped(self) -> Response:
        """
        Handles the event when playback is stopped.
        This method only saves the playback offset and returns the response.
        Returns:
            Response: The response object with no output speech.
        """
        self.logger.debug('In playback_stopped()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")

        playback_info["offset_in_ms"] = self.handler_input.request_envelope.request.offset_in_milliseconds

        return self.handler_input.response_builder.response

    def playback_nearly_finished(self, section) -> Response:
        """
        Handles the event when playback is nearly finished.
        This method retrieves the next track and queues it for playback.
        Returns:
            Response: The response object with the enqueue directive and the next track
            in audio item format. If there are no more tracks, the response object is empty.
        """
        self.logger.debug('In playback_nearly_finished()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")

        if playback_info.get("next_stream_enqueued"):
            return self.handler_input.response_builder.response

        next_track = self.playlist.get_next_track(False)
        if next_track == None:
            return self.handler_input.response_builder.response

        current_track = self.playlist.get_current_track()
        playback_info["next_stream_enqueued"] = True
        self.logger.info(f'Queuing next track: {next_track["title"]} by {next_track["artist"]}')

        from ask_sdk_model.interfaces.audioplayer import PlayDirective, PlayBehavior

        directive = PlayDirective(play_behavior=PlayBehavior.ENQUEUE, audio_item=self.playback.track_to_audio_item(next_track, 0, current_track["id"], section))
        self.handler_input.response_builder.add_directive(directive).set_should_end_session(True)

        return self.handler_input.response_builder.response

    def playback_finished(self) -> Response:
        """
        Handles the event when playback is finished.
        This method only updates the next playback index (the enqueue is already
        done in the PlaybackNearlyFinishedHandler), resets the playback_session and
        next_stream_enqueued flags and sets the track's offset to 0.
        Returns:
            Response: The response object with no output speech.
        """
        self.logger.debug('In playback_finished()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")

        # get next track just to update the index
        next_track = self.playlist.get_next_track(True)
        if next_track == None:
            return self.handler_input.response_builder.response

        playback_info["in_playback_session"] = False
        playback_info["next_stream_enqueued"] = False
        playback_info["offset_in_ms"] = 0

        self.logger.info(f'Next track: {next_track["title"]} by {next_track["artist"]} updated')
        return self.handler_input.response_builder.response

    def playback_failed(self, section) -> Response:
        """
        Handles the playback failure scenario
        This method is called when a playback failure occurs. It logs the event,
        and tries with the next track in the queue.
        Returns:
            Response: The response object with no output speech.
        """
        self.logger.debug('In playback_failed()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes

        return self.playback.next_playback(section)
