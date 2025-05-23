

def sentence_to_snake_case(input_string: str) -> str:
    """convert a sentence-type string (String with spaces and Capitals) to a snake_type

    Args:
        input_string (str): input string
    
    Returns:
        snake_type_string
    """

    return input_string.replace(" ", "_").replace(".", "_").lower()