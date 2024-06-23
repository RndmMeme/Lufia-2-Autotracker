import pymem
import time
import psutil

def read_memory_with_retry(process, address, size, retries=3, delay=1):
    attempt = 0
    while attempt < retries:
        try:
            memory_value = pymem.memory.read_bytes(process.process_handle, address, size)
            return memory_value
        except pymem.exception.MemoryReadError as e:
            print(f"Memory read error at address 0x{address:X}: {e}, retrying...")
            time.sleep(delay)
            attempt += 1
    raise pymem.exception.MemoryReadError(f"Failed to read memory at address 0x{address:X} after {retries} attempts")

def check_game_running(app, process, base_address, debug=False):
    try:
        gold = read_memory_with_retry(process, base_address + app.GOLD_ADDRESS, 2, debug=debug)
        if debug:
            print(f"In-game gold: {int.from_bytes(gold, 'little')}")
        return True
    except Exception as e:
        if debug:
            print(f"Error checking if game is running: {e}")
        return False

def read_memory(process, address, size, debug=False):
    """
    Read memory from a process.

    :param process: pymem.Pymem instance for the target process.
    :param address: Memory address to read from.
    :param size: Number of bytes to read.
    :param debug: If True, print debug information.
    :return: Bytes read from memory.
    """
    if process is None or address is None:
        print("Error: process or address is None in read_memory.")
        return None
    
    try:
        if debug:
            print(f"Reading {size} bytes from address 0x{address:X}")
        return pymem.memory.read_bytes(process.process_handle, address, size)
    except pymem.exception.MemoryReadError as e:
        if e.error_code == 299:  # Partial copy error handling
            if debug:
                print(f"Partial copy error at address 0x{address:X}, retrying...")
            time.sleep(1)
            return read_memory(process, address, size, debug=debug)
        if debug:
            print(f"Memory read error at address 0x{address:X}: {e}")
        raise

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