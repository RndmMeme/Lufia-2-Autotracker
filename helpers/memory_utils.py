# memory_utils.py

import pymem
import time
import psutil
import logging

def read_memory_with_retry(process, address, size, retries=3, delay=1):
    attempt = 0
    while attempt < retries:
        try:
            memory_value = pymem.memory.read_bytes(process.process_handle, address, size)
            return memory_value
        except pymem.exception.MemoryReadError as e:
            logging.error(f"Memory read error at address 0x{address:X}: {e}, retrying...")
            time.sleep(delay)
            attempt += 1
    raise pymem.exception.MemoryReadError(f"Failed to read memory at address 0x{address:X} after {retries} attempts")

def check_game_running(app, process, base_address):
    try:
        gold = read_memory_with_retry(process, base_address + app.GOLD_ADDRESS, 2)
        return True
    except Exception as e:
        logging.error(f"Error checking if game is running: {e}")
        return False

def read_memory(process, address, size):
    try:
        raw_bytes = process.read_bytes(address, size)
        if raw_bytes:
            return raw_bytes
        else:
            raise ValueError(f"Failed to read memory at address: 0x{address:X}")
    except Exception as e:
        logging.error(f"Error reading memory from address 0x{address:X}, size: {size}: {e}")
        return None

def is_process_running(process_name_substring):
    """
    Check if any process containing the specified substring in its name is running.
    
    Args:
        process_name_substring (str): Substring to search for in process names.

    Returns:
        str or None: The name of the first matching process, or None if no matching process is found.
    """
    for proc in psutil.process_iter(['name']):
        try:
            if process_name_substring.lower() in proc.info['name'].lower():
                return proc.info['name']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None