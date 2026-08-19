from typing import List, Dict, Optional, Tuple
from logging import Logger

from ask_sdk_model import Response

from ask_sdk_core.handler_input import HandlerInput

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
        PlexServerインスタンスを生成し、サーバーへの接続を確立する。
        接続は以下の優先順位で試行される：
        1. 設定 (`config.PMS_USE_SERVER_URL`) が有効な場合、指定されたURLとトークンで直接接続。
        2. 無効な場合は MyPlexAccount を経由し、対象のリソース（サーバー名）を取得。
        3. 取得したリソースの接続リストから、外部接続かつHTTPS（plex.direct）URLを探して接続試行。
        4. 上記が失敗、または見つからない場合、`resource.connect()` による自動フォールバック。

        Returns:
            PlexServer: 接続が確立されたPlexServerオブジェクト。

        Raises:
            Exception: 有効な接続先が見つからない場合や、MyPlexへの認証に失敗した場合、
                       またはすべての接続試行がタイムアウトした場合にスローされる。
        """
        if config.PMS_USE_SERVER_URL:
            return PlexServer(config.PMS_SERVER_URL, config.PMS_SERVER_TOKEN)
        plex_server = None
        account = MyPlexAccount(token=config.PMS_SERVER_TOKEN)
        resource = account.resource(config.PMS_SERVER_NAME)
        target_url = next((c.uri for c in resource.connections if not c.local and c.uri.startswith('https') and "plex.direct" in c.uri), None)
        if target_url:
            try:
                plex_server = PlexServer(target_url, config.PMS_SERVER_TOKEN, timeout=3)
            except Exception as exception:
                self.logger.warning(f"Direct URL connection failed: {exception}. Falling back to resource.connect()")
        if plex_server is None:
            plex_server = resource.connect(timeout=3)
        return plex_server

    def connect_plex(self) -> Tuple[bool, Optional[Response]]:
        """
        Plexサーバーおよび指定されたライブラリセクションへの接続を確立する。
        すでに接続済み（キャッシュあり）の場合は、接続処理をスキップして正常終了を返す。
        未接続の場合は設定に基づきサーバーへ接続し、対象のセクション（Music等）をクラス変数 `_section` にキャッシュする。

        Returns:
            Tuple[bool, Optional[Response]]: 
                - bool: 接続成功時は True、失敗時は False。
                - Response: 失敗時はユーザーにエラーを伝えるための応答オブジェクト。
                           成功時は None。

        Raises:
            NotFound: 指定されたセクション名がサーバー内に存在しない場合。
            Exception: 認証失敗、タイムアウト、ネットワーク不通などの接続エラー。
        """
        self.logger.debug('In connect_plex()')

        if PlexConnector._section is not None:
            self.logger.debug('Already connected.')
            return True, None

        self.logger.info(f"Connecting to section: {config.PMS_DEFAULT_SECTION_NAME}")

        # get localization data
        data = self.handler_input.attributes_manager.request_attributes["_"]

        try:
            plex_server = self._create_plex_server()
            section = plex_server.library.section(config.PMS_DEFAULT_SECTION_NAME)
            PlexConnector._section = section
            self.logger.info('Successfully connected to section.')
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
        ユーザーにエラーを通知し、再試行を促すための応答オブジェクトを生成する。

        Args:
            speak_output (str): ユーザーに対して読み上げるエラーメッセージの内容。

        Returns:
            Response: speak および ask プロパティが設定された Alexa SDK の Response オブジェクト。
                      これにより、音声出力の後にマイクがオープンになり、ユーザーの応答を待つ。
        """
        return (
            self.handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
