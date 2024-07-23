import json
import os
from PIL import Image, ImageTk
from pathlib import Path
import logging

# Caching dictionaries
json_cache = {}
image_cache = {}

def load_json(file_path):
    """
    Load JSON data from a file with caching to improve performance on repeated accesses.
    
    :param file_path: Path to the JSON file.
    :return: Parsed JSON data as a dictionary, or an empty dictionary if an error occurs.
    """
    file_path = Path(file_path)
    if file_path in json_cache:
        return json_cache[file_path]
    
    try:
        if file_path.is_dir():
            logging.error(f"{file_path} is a directory, not a file.")
            return {}

        with file_path.open("r") as file:
            data = json.load(file)
            json_cache[file_path] = data  # Cache the loaded JSON data
            return data
    except json.JSONDecodeError as e:
        logging.error(f"Error loading JSON from {file_path}: {e}")
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
    except PermissionError:
        logging.error(f"Permission denied for file: {file_path}")
    except Exception as e:
        logging.error(f"Unexpected error loading JSON from {file_path}: {e}")
    
    return {}

def load_image(path, size=(30, 30)):
    """
    Load an image from a file, resize it, and cache the result to improve performance on repeated accesses.
    
    :param path: Path to the image file.
    :param size: Tuple specifying the target size (width, height). Default is (30, 30).
    :return: ImageTk.PhotoImage object or None if an error occurs.
    """
    path = Path(path)
    cache_key = (str(path), size)
    if cache_key in image_cache:
        return image_cache[cache_key]
    
    try:
        image = Image.open(path)
        image = image.resize(size, Image.Resampling.LANCZOS)
        photo_image = ImageTk.PhotoImage(image)
        image_cache[cache_key] = photo_image  # Cache the loaded and resized image
        return photo_image
    except Exception as e:
        logging.error(f"Error loading image at {path}: {e}")
        return None
