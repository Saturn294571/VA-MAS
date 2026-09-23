import json
import yaml
import re

def find_correct_data(dict_data, guard_keys=[]):
    # If the current layer contains the correct key, return the current layer
    hit = True
    for key in guard_keys:
        if key not in dict_data.keys():
            hit = False
    if hit:
        return dict_data
    # Otherwise, iterate through every key in the current layer
    for key in dict_data:
        # If the current key's value is a dictionary, search recursively
        if isinstance(dict_data[key], dict):
            result = find_correct_data(dict_data[key], guard_keys)
            # If a layer containing the correct key is found, return the result
            if result is not None:
                return result
        # If the current key's value is a list, iterate through each element in the list
        elif isinstance(dict_data[key], list):
            result_list = []
            for item in dict_data[key]:
                # If an element in the list is a dictionary, search recursively
                if isinstance(item, dict):
                    result = find_correct_data(item, guard_keys)
                    # If a layer containing the correct key is found, return the result
                    if result is not None:
                        if isinstance(result, list):
                            result_list += result
                        else:
                            result_list.append(result)
            if len(result_list) > 0:
                return result_list
    # If not found, return None
    return None


def _fix_missing_commas_in_object(s: str) -> str:
    """
    修复一种常见 LLM 错误：JSON 对象中 key-value 对之间漏写逗号
    例如：{"a": 1 "b": 2} -> {"a": 1, "b": 2}

    原理：当我们看到下一个 key 的起始形态 `"xxx":` 时，
    如果它前面紧挨着的内容看起来像“一个 value 已经结束”（如字符串结束引号、数字、}、] 等），
    就在它前面插入逗号。
    """
    return re.sub(
        # (?="[^"]+"\s*:)  This ensures that a "key": actually follows
        # Lookbehind constraint: the previous character resembles a value terminator
        r'(?<=[0-9"\}\]])\s*(?="[^"]+"\s*:)',
        ', ',
        s
    )


def extract_info(text: str, guard_keys=[]) -> [dict]:
    try:
        # Initialize an empty list to store the extracted dictionaries
        info_list = []

        # Initialize an empty string to store the current dictionary text
        dict_text = ''
        
        # Initialize a counter for the number of open braces
        brace_count = 0

        # Iterate over each character in the text
        for char in text:
            # If the character is a '{', increase the brace count and add it to the dictionary text
            if char == '{':
                brace_count += 1
                dict_text += char
            # If the character is a '}', decrease the brace count
            elif char == '}':
                brace_count -= 1
                dict_text += char
                # If the brace count is zero, it's the end of a dictionary
                if brace_count == 0:
                    # json False -> false True -> true None -> null
                    dict_text = dict_text.replace("False", "false").replace("True", "true").replace("None", "null")
                    # Handle annotation string // annotation
                    dict_text = re.sub(r'//.*?\n', '\n', dict_text)

                    # Comma fix
                    dict_text = _fix_missing_commas_in_object(dict_text)

                    try:
                        # Convert the dictionary text to a dictionary and add it to the list
                        dict_data = json.loads(dict_text)
                    except Exception as e:
                        print(f"extract with json error, try yaml \n{e}\nerror text:\n{dict_text}")
                        dict_data = None
                    if dict_data is None:
                        # If conversion fails, try using yaml
                        dict_data = yaml.load(dict_text, Loader=yaml.FullLoader)
                    # There is a case where the llm wraps the data, resulting in a format like {"data":{...}} or {"task":{...}}
                    # In this case, we need to extract the data
                    # Assume the correct key for the first layer is description
                    correct_data = find_correct_data(dict_data, guard_keys)
                    if correct_data is not None:
                        if isinstance(correct_data, list):
                            info_list += correct_data
                        else:
                            info_list.append(correct_data)
                    else:
                        print(f"Warning: {guard_keys} not found in {dict_data}")
                    # Reset the dictionary text
                    dict_text = ''
            # If the character is neither '{' nor '}', add it to the dictionary text if it's part of a dictionary
            elif brace_count > 0:
                dict_text += char
        return info_list
    except Exception as e:
        print(f"extract_info error: {e}")
        return []
