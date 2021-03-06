"""GCode Procedure"""

import decimal
import string

try:
    from . import GCodeObject
except SystemError:
    import GCodeObject

class GCodeParser:
    """Parse the GCode into tuple with elements.

Overview:
This class handle str and convert it into GCodeObject.GCode.

Example:
'X-12.0056'
    * lexical_parse()
(GCodeObject.GCodeParserChar('X'), GCodeObject.GCodeParserMinus('-'), \
GCodeObject.GCodeParserInt(12), GCodeObject.GCodeParserDot('.'), \
GCodeObject.GCodeParserDigitAfterDot(2), GCodeObject.GCodeParserInt(56))
    * trim_comment_and_specials()
    * bind_float()
(GCodeObject.GCodeParserChar('X'), GCodeObject.GCodeParserFloat(12.0056))
    * bind_to_gcode()
(GCodeObject.GCode(GCodeObject.GCodeChar('x'), GCodeObject.GCodeInt(12.0056)))

Supported characters:
'char', 'int', 'space', '-', '.', '(', ')', '%', "'", '"'"""
    string_original = str()
    list_lexical_parse = list()
    list_trim_comment_and_specials = list()
    list_bind_float = list()
    list_bind_to_gcode = list()

    def __init__(self, string_process):
        self.string_original = string_process

    def run(self):
        """Run all the GCodeParser's methods"""
        self.lexical_parse()
        self.trim_comment_and_specials()
        self.bind_float()
        self.bind_to_gcode()
        return tuple(self.list_bind_to_gcode)

    def lexical_parse(self):
        # pylint: disable=too-many-branches
        """Lexical parse, form text file to Python tuple.

Notice:
This function is designed without regular expressions."""
        main_loop = True
        idx = int()
        result_list = list()
        last_processed_type = GCodeObject.GCodeParserSpace
        # Replacement form newline('\n') to '%'
        held_string = self.string_original.replace('\n', '%')
        while main_loop:
            # Check EOF and replace character with space
            if idx == len(held_string):
                character = ' '
                main_loop = False
            else:
                character = held_string[idx]

            # 'char'
            if character in string.ascii_letters:
                result_list.append(GCodeObject.GCodeParserChar(character.upper()))
                last_processed_type = GCodeObject.GCodeParserChar
            # 'zero' after dot(.) or ordinary int
            elif character.isdigit():
                if last_processed_type == GCodeObject.GCodeParserDot:
                    if character == '0':
                        result_list.append(GCodeObject.GCodeParserDigitAfterDot(1))
                        last_processed_type = GCodeObject.GCodeParserDigitAfterDot
                    else:
                        result_list.append(GCodeObject.GCodeParserInt(int(character)))
                        last_processed_type = GCodeObject.GCodeParserInt
                elif last_processed_type == GCodeObject.GCodeParserDigitAfterDot:
                    if character == '0':
                        result_list[-1].element += 1
                        last_processed_type = GCodeObject.GCodeParserDigitAfterDot
                    else:
                        result_list.append(GCodeObject.GCodeParserInt(int(character)))
                        last_processed_type = GCodeObject.GCodeParserInt
                elif last_processed_type == GCodeObject.GCodeParserInt:
                    result_list[-1] = GCodeObject.GCodeParserInt \
                                            (int(result_list[-1]) * 10 + int(character))
                    last_processed_type = GCodeObject.GCodeParserInt
                else:
                    result_list.append(GCodeObject.GCodeParserInt(int(character)))
                    last_processed_type = GCodeObject.GCodeParserInt
            # 'space'
            elif character.isspace():
                last_processed_type = GCodeObject.GCodeParserSpace
            # '-'
            elif character == '-':
                result_list.append(GCodeObject.GCodeParserMinus(character))
                last_processed_type = GCodeObject.GCodeParserMinus
            # '.'
            elif character == '.':
                result_list.append(GCodeObject.GCodeParserDot(character))
                last_processed_type = GCodeObject.GCodeParserDot
            # '('
            elif character == '(':
                result_list.append(GCodeObject.GCodeParserBracketLeft(character))
                last_processed_type = GCodeObject.GCodeParserBracketLeft
            # ')'
            elif character == ')':
                result_list.append(GCodeObject.GCodeParserBracketRight(character))
                last_processed_type = GCodeObject.GCodeParserBracketRight
            # '%', "'", '"'
            elif character == '%' or  "'" or '"':
                result_list.append(GCodeObject.GCodeParserSpecialCharacter(character))
                last_processed_type = GCodeObject.GCodeParserSpecialCharacter
            else:
                raise GCodeObject.GCodeSyntaxError \
                    ('The file contains unsupported character', idx, character)

            idx += 1
        self.list_lexical_parse = result_list
        return tuple(result_list)

    def trim_comment_and_specials(self):
        """Trim the comment and special characters."""
        list_before = list(self.list_lexical_parse)
        list_trimmed_specials = list()
        list_trimmed_twofold = list()

        # Eliminate special characters
        for piv in list_before:
            if isinstance(piv, GCodeObject.GCodeParserSpecialCharacter):
                continue
            else:
                list_trimmed_specials.append(piv)

        # Eliminate comments
        indent_level_head = 0
        indent_level_tail = 0
        for piv in list_trimmed_specials:
            if isinstance(piv, GCodeObject.GCodeParserBracketLeft):
                indent_level_head += 1
            elif isinstance(piv, GCodeObject.GCodeParserBracketRight):
                indent_level_head -= 1

            if indent_level_head == 0 and indent_level_tail == 0:
                list_trimmed_twofold.append(piv)

            # Check invalid indent level
            if indent_level_head < 0:
                raise GCodeObject.GCodeSyntaxError('Invalid comment wrapping', piv)

            indent_level_tail = indent_level_head

        if indent_level_head:
            raise GCodeObject.GCodeSyntaxError('Invalid comment wrapping indent level' \
                                                                , indent_level_head)

        self.list_trim_comment_and_specials = list_trimmed_twofold
        return tuple(list_trimmed_twofold)

    def bind_float(self):
        # pylint: disable=too-many-branches
        """Bind the floats"""
        list_before = self.list_trim_comment_and_specials
        list_result = list()
        list_location_digitafterdot = list()
        list_location_num = list()
        list_location_dot = list()
        list_location_minus_valid = list()

        # Check numbers' locations and dots' locations
        for index in range(0, len(list_before)):
            # Check dots' (after digits) locations
            if isinstance(list_before[index], GCodeObject.GCodeParserDigitAfterDot):
                list_location_digitafterdot.append(index)
            # (If list_before[index] is not GCodeObject.GCodeParserDigitAfterDot,
            # it will be ordinary numbers.)
            # Check numbers' locations
            elif isinstance(list_before[index].element, int) or \
                isinstance(list_before[index].element, float):
                list_location_num.append(index)
            # Check numbers' locations
            if isinstance(list_before[index], GCodeObject.GCodeParserDot):
                list_location_dot.append(index)
            # Check whether minus(-) is valid
            if isinstance(list_before[index - 1], GCodeObject.GCodeParserMinus) and \
                    isinstance(list_before[index], GCodeObject.GCodeParserInt):
                list_location_minus_valid.append(index - 1)

        # Check whether dot(.) is sealed with integars.
        for index in list_location_dot:
            try:
                if isinstance(list_before[index - 1], GCodeObject.GCodeParserInt) and \
                    (True if isinstance(list_before[index + 1], GCodeObject.GCodeParserInt) or \
                    isinstance(list_before[index + 1], GCodeObject.GCodeParserDigitAfterDot) \
                                                                                else False):
                    pass
                else:
                    raise GCodeObject.GCodeSyntaxError('Dot(.) is not sealed with integers', index)
            except IndexError:
                if index == 1:
                    continue
                elif index + 1 == len(list_before):
                    raise GCodeObject.GCodeSyntaxError('Dot(.) is located in EOF', index)

        # Bind
        for index in range(0, len(list_before)):
            # Initialize variables
            actual_spot_minuscheck = False
            calculated = decimal.Decimal(1)

            # Prefixes
            if not index - 1 in list_location_dot and \
                not index in list_location_dot and \
                not index + 1 in list_location_dot and \
                (False if isinstance(list_before[index], GCodeObject.GCodeParserInt) and \
                index - 2 in list_location_dot else True) and \
                not index - 1 in list_location_minus_valid and \
                not index in list_location_minus_valid:
                list_result.append(list_before[index])
            # Floats - it works with dots
            elif index in list_location_dot:
                # Initialize variables
                actual_number_len = 0
                actual_number_spot = None
                actual_number_value = None
                try:
                    if isinstance(list_before[index + 1], GCodeObject.GCodeParserDigitAfterDot) and\
                        isinstance(list_before[index + 2], GCodeObject.GCodeParserInt):
                        actual_number_spot = index + 2
                    elif isinstance(list_before[index + 1], GCodeObject.GCodeParserInt):
                        actual_number_spot = index + 1
                except IndexError:
                    pass

                try:
                    if actual_number_spot == index + 2:
                        actual_number_len -= list_before[index + 1].element
                    while actual_number_len < len(str(list_before[actual_number_spot].element)):
                        calculated = calculated * decimal.Decimal('0.1')
                        actual_number_len += 1
                # If actual_number_spot is None, list raises TypeError.
                except TypeError:
                    actual_number_value = 0
                # If len() didn't raised TypeError, actual_number_value is this:
                if actual_number_value is None:
                    actual_number_value = list_before[actual_number_spot].element

                calculated = calculated * decimal.Decimal(actual_number_value)
                calculated = list_before[index - 1].element + calculated
                list_result.append(GCodeObject.GCodeParserFloat(float(calculated)))
                actual_spot_minuscheck = True
            # Integers - it works with integers
            elif index in list_location_num and \
                    not index - 1 in list_location_digitafterdot and \
                    not index - 1 in list_location_dot and \
                    not index + 1 in list_location_dot:
                list_result.append(list_before[index])
                actual_spot_minuscheck = True

            # Check minus and reverse
            if actual_spot_minuscheck:
                if (True if index - 2 in list_location_minus_valid and \
                            index in list_location_dot else False) or \
                    (True if index - 1 in list_location_minus_valid and \
                            index in list_location_num else False):
                    list_result[-1].element = -list_result[-1].element

        # Find the unused GCodeObject objects
        for elem in list_result:
            if isinstance(elem, GCodeObject.GCodeParserMinus) or \
                isinstance(elem, GCodeObject.GCodeParserDot):
                raise GCodeObject.GCodeSyntaxError('Check minus(-) or Dot(.)', elem)

        self.list_bind_float = list_result
        return tuple(list_result)

    def bind_to_gcode(self):
        # pylint: disable=redefined-variable-type
        """Bind the list into G-code object"""
        list_before = self.list_bind_float
        odd = False
        tem_prefix = None
        tem_number = None
        list_result = list()

        for index in list_before:
            odd = not odd
            if odd and isinstance(index, GCodeObject.GCodeParserChar):
                tem_prefix = index
            elif not odd and isinstance(index, GCodeObject.GCodeParserNumberBase):
                if isinstance(index, GCodeObject.GCodeParserInt):
                    tem_number = GCodeObject.GCodeInt(index.element)
                else:
                    tem_number = GCodeObject.GCodeFloat(index.element)
                list_result.append(GCodeObject.GCode( \
                                    GCodeObject.GCodePrefix(tem_prefix.element), tem_number))
            else:
                raise GCodeObject.GCodeSyntaxError('Check the sequence of prefixes and numbers' \
                                                                                        , index)

        # If odd is True, g-code sequence does not ends with number.
        if odd:
            raise GCodeObject.GCodeSyntaxError('G-code ends with numbers')

        self.list_bind_to_gcode = list_result
        return tuple(list_result)
