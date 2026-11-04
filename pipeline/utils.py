from common.logging import init_logger
from common.parsing import find_correct_data, _fix_missing_commas_in_object, parse_info
import re
import json
import logging
import colorlog
import os
import yaml
import sys

from typing import Union

import functools
import time

def timed_cache(max_age):
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal cache
            current_time = time.time()
            key = (args, tuple(sorted(kwargs.items())))
            # key to string
            key = str(key)
            
            # Check if the cache entry exists and is still valid
            if key in cache and current_time - cache[key]['timestamp'] < max_age:
                return cache[key]['value']
            
            # Call the function and cache the result
            value = func(*args, **kwargs)
            cache[key] = {'value': value, 'timestamp': current_time}
            
            # Optional: Clean up expired cache entries
            expired_keys = [k for k, v in cache.items() if current_time - v['timestamp'] >= max_age]
            for k in expired_keys:
                del cache[k]
            
            return value
        return wrapper
    return decorator


def format_string(template: str, data: dict) -> str:
    # Check if all {{}} in the template are present in data
    keys = re.findall(r'{{(.*?)}}', template)
    for key in keys:
        if key not in data:
            raise ValueError(f'when format:\n{template} \nkey {key} not found in data')

    # Replace {{}} with values from data
    for key, value in data.items():
        template = template.replace('{{' + key + '}}', str(value))
    return template


def document2string(document: Union[dict, list[dict]], MAX_LENGTH=2048, MIN_VALUE_LENGTH=128) -> str:
    MAX_LENGTH = MAX_LENGTH  # Set your own threshold
    MIN_VALUE_LENGTH = MIN_VALUE_LENGTH  # Set your own threshold
    if isinstance(document, dict):
        document = [document]

    if len(str(document)) > MAX_LENGTH:
        # If the document is too long, only display the keys and the number of data
        keys = ', '.join(document[0].keys())
        summary = f'The document has {len(str(document))} words. Due to the large amount of data, not all information can be displayed. The keys are: {keys}. '
        # Check the length of each value, if it's short enough, display it
        for doc in document:
            for key, value in doc.items():
                if len(str(value)) <= MIN_VALUE_LENGTH:
                    summary += f'{key}: {value}, '
        return summary
    else:
        # If the document is not too long, display all the information
        return str(document)


def extract_info(text: str, guard_keys: list[str] = []) -> list[dict]:
    """Pipeline compatibility parser; legacy type errors propagate."""
    return parse_info(text, guard_keys, recover_yaml_errors=True)


def smart_truncate(data, max_length):
    max_length = 4 * max_length # tokenization will increase the length of the text
    def truncate_non_strings(item):
        if isinstance(item, dict):
            new_dict = {k: truncate_non_strings(v) for k, v in item.items()}
            if all(value == '...' for value in new_dict.values()):
                return '...'  # Collapse entire dict if all values are '...'
            return new_dict
        elif isinstance(item, list):
            new_list = [truncate_non_strings(elem) for elem in item]
            if all(elem == '...' for elem in new_list):
                return '...'  # Collapse entire list if all elements are '...'
            return new_list
        elif isinstance(item, str):
            return item  # Keep strings intact
        else:
            return '...'  # Replace non-string scalar values with '...'

    def truncate_strings(item, max_str_length):
        if isinstance(item, dict):
            new_dict = {k: truncate_strings(v, max_str_length) for k, v in item.items()}
            if all(isinstance(value, str) and value.endswith('...') for value in new_dict.values()):
                return '...'  # Collapse entire dict if all values are truncated strings
            return new_dict
        elif isinstance(item, list):
            new_list = [truncate_strings(elem, max_str_length) for elem in item]
            if all(isinstance(elem, str) and elem.endswith('...') for elem in new_list):
                return '...'  # Collapse entire list if all elements are truncated strings
            return new_list
        elif isinstance(item, str) and len(item) > max_str_length:
            return item[:max_str_length] + '...'  # Truncate long strings
        else:
            return item

    if len(str(data)) <= max_length:
        return json.dumps(data, ensure_ascii=False)
    # First stage: truncate non-string data
    truncated_data = truncate_non_strings(data)
    json_str = json.dumps(truncated_data, ensure_ascii=False)
    

    # Second stage: truncate strings if necessary
    max_str_length = max_length
    # print(f"The data {len(json_str)} truncating the strings to {max_str_length} characters...")
    while len(json_str) > max_length:
        max_str_length -= 1  # Reduce the allowed string length
        truncated_data = truncate_strings(truncated_data, max_str_length)
        json_str = json.dumps(truncated_data, ensure_ascii=False)

    return json_str


def flatten_json(y, threshold=200):
    # This function converts any JSON file into a 1D dict for easier retrieval search
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            if len(str(x)) < threshold:
                out[name[:-1]] = x
                # print(x)
            else:
                for a in x:
                    flatten(x[a], name + a + '_')
        elif type(x) is list:
            if len(str(x)) < threshold:
                out[name[:-1]] = str(x)
                # print(x)
            else:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out

# if __name__ == "__main__":
#     response = """
# {
#   "subtasks": [
#     {
#       "subtask description": "Gather necessary materials",
#       "milestones": [
#         "Identify the required materials from the blueprint data",
#         "Locate the materials in the vicinity"
#       ],
#       "related data": [
#         "Blueprint data",
#         "Blocks in the vicinity"
#       ]
#     },
#     {
#       "subtask description": "Prepare the construction site",
#       "milestones": [
#         "Identify the location specified in the blueprint data",
#         "Clear the area if necessary",
#         "Ensure the area is suitable for construction"
#       ],
#       "related data": [
#         "Blueprint data",
#         "Current location of the agents"
#       ]
#     },
#     {
#       "subtask description": "Build the construction according to the blueprint",
#       "milestones": [
#         "Follow the blueprint data to place the cut sandstone block at the specified position and facing direction",
#         "Place the terracotta block at the specified position and facing direction",
#         "Install the torch at the specified position and facing direction"
#       ],
#       "related data": [
#         "Blueprint data",
#         "Cut sandstone block",
#         "Terracotta block",
#         "Torch"
#       ]
#     }
#   ]
# }"""
#     result = extract_info(response, ["related data"]) 
#     print(result)
