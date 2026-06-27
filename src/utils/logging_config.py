import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
import sys
import threading

from utils.version import APP_VERSION
from utils.constants import USER_DATA_DIR


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"


def get_log_directory() -> Path:
    return USER_DATA_DIR / "logs"


def configure_logging() -> Path:
    """Configure durable session and error logs and return their directory."""
    log_dir = get_log_directory()
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT)

    tracker_handler = RotatingFileHandler(
        log_dir / "tracker.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    tracker_handler.setLevel(logging.INFO)
    tracker_handler.setFormatter(formatter)
    root.addHandler(tracker_handler)

    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    if sys.stderr is not None:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    logging.captureWarnings(True)
    _install_exception_hooks()
    logging.getLogger(__name__).info(
        "Session started | version=%s | frozen=%s | python=%s | os=%s",
        APP_VERSION,
        bool(getattr(sys, "frozen", False)),
        platform.python_version(),
        platform.platform(),
    )
    return log_dir


def _install_exception_hooks() -> None:
    default_sys_hook = sys.__excepthook__

    def handle_main_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            default_sys_hook(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger("uncaught").critical(
            "Uncaught exception in main thread",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    def handle_thread_exception(args):
        logging.getLogger("uncaught").critical(
            "Uncaught exception in thread '%s'",
            args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = handle_main_exception
    threading.excepthook = handle_thread_exception


def install_qt_message_logging() -> None:
    """Route Qt diagnostics into the same durable log files."""
    from PyQt6.QtCore import QtMsgType, qInstallMessageHandler

    def qt_message_handler(message_type, context, message):
        logger = logging.getLogger("qt")
        location = ""
        if context and context.file:
            location = f" | {context.file}:{context.line}"
        text = f"{message}{location}"
        if message_type == QtMsgType.QtFatalMsg:
            logger.critical(text)
        elif message_type == QtMsgType.QtCriticalMsg:
            logger.error(text)
        elif message_type == QtMsgType.QtWarningMsg:
            logger.warning(text)
        elif message_type == QtMsgType.QtInfoMsg:
            logger.info(text)
        else:
            logger.debug(text)

    qInstallMessageHandler(qt_message_handler)
