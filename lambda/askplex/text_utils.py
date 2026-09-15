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

    @staticmethod
    def _normalize_query(name: str) -> str:
        """
        Normalizes an query for fuzzy matching by handling common variations.

        Args:
            name (str): The query to normalize.

        Returns:
            str: The normalized query.
        """
        # Convert to lowercase and strip whitespace
        normalized = name.lower().strip()

        # Replace common variations
        replacements = {
            '&': 'and',
            'and': '&',
            '+': 'and',
            'feat.': 'featuring',
            'featuring': 'feat.',
            'ft.': 'featuring',
            'vs.': 'versus',
            'versus': 'vs.',
            "'": "’"
        }

        # Apply replacements (both directions for flexibility)
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        # Remove extra spaces and special characters
        normalized = ' '.join(normalized.split())

        return normalized

    def _normalize(self, source: str) -> str:
        """
        Removes the skill name if it is mixed into the slot value and normalizes it.
        Also converts kanji numerals to numbers.

        Args:
            source (str): The string to normalize
        
        Returns:
            str: The normalized string
        """
        result = source.replace(config.SKILL_INVOCATION_NAME, "").strip()
        # Particles like "〜で" (using) and "〜を使って" (using) may also be mixed in, so normalize
        result = source.replace("で", "").replace("を使って", "")
        result = self._convert_kanji_to_int(result)
        return result

    def _convert_kanji_to_int(self, source) -> str:
        """
        Converts kanji numerals to numbers.
        
        Args:
            source (str): String containing kanji numerals
        
        Returns:
            str: String with kanji numerals converted to numbers
        """
        result = source.translate(str.maketrans("零〇一壱二弐三参四五六七八九拾", "00112233456789十", ""))
        convert_table = {"十": "0", "百": "00", "千": "000", "万": "0000", "億": "00000000", "兆": "000000000000", "京": "0000000000000000"}
        unit_list = "|".join(convert_table.keys())
        while re.search(unit_list, result):
            for unit in convert_table.keys():
                zeros = convert_table[unit]
                for numbers in re.findall(rf"(\d+){unit}(\d+)", result):
                    result = result.replace(numbers[0] + unit + numbers[1], numbers[0] + zeros[len(numbers[1]):len(zeros)] + numbers[1])
                for number in re.findall(rf"(\d+){unit}", result):
                    result = result.replace(number + unit, number + zeros)
                for number in re.findall(rf"{unit}(\d+)", result):
                    result = result.replace(unit + number, "1" + zeros[len(number):len(zeros)] + number)
                result = result.replace(unit, "1" + zeros)
        return result

    def strip_specials(self, source: str) -> str:
        """
        Strips all special characters from the passed in string.
        This helps match titles like "gimme gimme gimme" with "gimme! gimme! gimme!".

        Args:
            source (str): The string to strip special characters from.

        Returns:
            str: The string with special characters removed.
        """
        # Remove all non-alphanumeric characters (except spaces)
        result = re.sub(r'[^\w\s]', '', source)
        # Remove extra spaces
        result = ' '.join(result.split())
        return result
