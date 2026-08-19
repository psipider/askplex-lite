import re
from logging import Logger

from ask_sdk_core.handler_input import HandlerInput

from . import config


class TextUtils:
    """
    Provides text normalization utilities including Japanese text processing and kanji number conversion.
    """

    def __init__(self, logger: Logger, handler_input: HandlerInput) -> None:
        """
        Initializes the text utilities with a logger and handler input.
        Args:
            logger (Logger): The logger instance to be used for logging.
            handler_input (HandlerInput): The handler input instance.
        """
        self.logger = logger
        self.handler_input = handler_input

    def _normalize(self, source: str) -> str:
        """
        スロット値にスキル名が混入していたら削除して正規化する。
        また、漢数字を数字に変換する。

        Args:
            source (str): 文字列
        
        Returns:
            str: 正規化された文字列
        """
        result = source.replace(config.SKILL_INVOCATION_NAME, "").strip()
        # 「〜で」や「〜を使って」などの助詞も混ざることがあるため、正規化
        result = source.replace("で", "").replace("を使って", "")
        result = self._convert_kanji_to_int(result)
        return result

    def _convert_kanji_to_int(self, source) -> str:
        """
        漢数字を数字に変換する。
        
        Args:
            source (str): 漢数字を含む文字列
        
        Returns:
            str: 漢数字を数字に変換した文字列
        """
        result = source.translate(str.maketrans("零〇一壱二弐三参四五六七八九拾", "00112233456789十", ""))
        convert_table = {"十": "0", "百": "00", "千": "000", "万": "0000", "億": "00000000", "兆": "000000000000", "京": "0000000000000000"}
        unit_list = "|".join(convert_table.keys())
        while re.search(unit_list, result):
            for unit in convert_table.keys():
                zeros = convert_table[unit]
                for numbers in re.findall(f"(\d+){unit}(\d+)", result):
                    result = result.replace(numbers[0] + unit + numbers[1], numbers[0] + zeros[len(numbers[1]):len(zeros)] + numbers[1])
                for number in re.findall(f"(\d+){unit}", result):
                    result = result.replace(number + unit, number + zeros)
                for number in re.findall(f"{unit}(\d+)", result):
                    result = result.replace(unit + number, "1" + zeros[len(number):len(zeros)] + number)
                result = result.replace(unit, "1" + zeros)
        return result
