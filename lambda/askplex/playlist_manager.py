import random
from typing import Dict
from logging import Logger

from ask_sdk_core.handler_input import HandlerInput


class PlaylistManager:
    """
    Manages playlist operations including track navigation and playlist manipulation.
    """

    def __init__(self, logger: Logger, handler_input: HandlerInput) -> None:
        """
        Initializes the playlist manager with a logger and handler input instance.
        Args:
            logger (Logger): The logger instance to be used for logging.
            handler_input (HandlerInput): The handler input instance.
        """
        self.logger = logger
        self.handler_input = handler_input

    def add_track(self, track: Dict, playback_info: Dict) -> None:
        """
        Adds a track to the playlist.
        Args:
            track (Dict): The track information
            playback_info (Dict): Playback info
        Returns:
            None
        """
        self.logger.debug('In add_track()')

        playlist_len = len(playback_info["playlist"])

        playback_info["playlist"][str(playlist_len)] = track
        playback_info["play_order"].append(playlist_len)

    def get_next_track(self, update_index: bool) -> Dict:
        """
        Retrieves the next track in the playlist.
        Returns:
            Dict: The next track information
        """
        self.logger.debug('In get_next_track()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_setting = persistence_attr.get("playback_setting")
        playback_info = persistence_attr.get("playback_info")

        index = int(playback_info["index"])
        playlist_len = len(playback_info["playlist"])

        if playlist_len == 0 or (index == (playlist_len - 1) and not playback_setting["loop"]):
            return None

        index = (index + 1) % playlist_len

        if update_index:
            playback_info["index"] = index
            playback_info["offset_in_ms"] = 0
            playback_info["playback_index_changed"] = True

        play_order = playback_info["play_order"]
        return playback_info["playlist"].get(str(play_order[index]))

    def get_previous_track(self) -> Dict:
        """
        Retrieves the previous track in the playlist.
        Returns:
            Dict: The previous track information
        """
        self.logger.debug('In get_previous_track()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_setting = persistence_attr.get("playback_setting")
        playback_info = persistence_attr.get("playback_info")

        index = int(playback_info["index"])
        playlist_len = len(playback_info["playlist"])

        if playlist_len == 0 or (index == 0 and not playback_setting["loop"]):
            return None

        index = (index - 1) if index > 0 else (playlist_len - 1)

        playback_info["index"] = index
        playback_info["offset_in_ms"] = 0
        playback_info["playback_index_changed"] = True

        play_order = playback_info["play_order"]
        return playback_info["playlist"].get(str(play_order[index]))

    def get_current_track(self) -> Dict:
        """
        Retrieves the current track information
        Returns:
            Dict: The current track information
        """
        self.logger.debug('In get_current_track()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")

        index = int(playback_info["index"])
        playlist_len = len(playback_info["playlist"])

        if index < playlist_len:
            play_order = playback_info["play_order"]
            return playback_info["playlist"].get(str(play_order[index]))

    def shuffle_play_order(self, shuffle: bool) -> None:
        """
        Adjusts the playback order of the playlist based on the shuffle parameter.
        If shuffle is True, the playback order is randomized, with the current index
        being moved to the start of the new order. If shuffle is False, the playback
        order is reset to the original order.
        Args:
            shuffle (bool): A flag indicating whether to shuffle the playback order.
        Returns:
            None
        """
        self.logger.debug('In shuffle_play_order()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_info = persistence_attr.get("playback_info")

        index = int(playback_info["index"])
        play_order = playback_info["play_order"]
        playlist_index = int(play_order[index])
        playlist_len = len(playback_info["playlist"])

        has_started = playback_info.get("has_started", False)

        play_order = list(range(playlist_len))

        if shuffle:
            if has_started:
                play_order.remove(playlist_index)
                random.shuffle(play_order)
                play_order.insert(0, playlist_index)
            else:
                random.shuffle(play_order)
            index = 0
        else:
            index = playlist_index

        playback_info["play_order"] = play_order
        playback_info["index"] = index
        playback_info["playback_index_changed"] = True

    def clear_playlist(self) -> None:
        """
        Clears the current playlist and resets playback settings.
        This method performs the following actions:
        - Disables shuffle and loop settings.
        - Resets the playback index and offset.
        - Marks the playback index as changed.
        - Clears the playlist.
        Returns:
            None
        """
        self.logger.debug('In clear_playlist()')
        persistence_attr = self.handler_input.attributes_manager.persistent_attributes
        playback_setting = persistence_attr.get("playback_setting")
        playback_info = persistence_attr.get("playback_info")

        playback_setting["shuffle"] = False
        playback_setting["loop"] = False

        playback_info["index"] = 0
        playback_info["offset_in_ms"] = 0
        playback_info["playback_index_changed"] = True
        playback_info["playlist"] = {}
        playback_info["play_order"] = []
