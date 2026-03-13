import logging
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text
from rich.traceback import install as install_rich_traceback

# Install rich traceback globally for better error display
install_rich_traceback(show_locals=True)


class CustomLogger:
    """
    Custom logger with Rich console output and file logging.
    Use this class to get consistent logging across the project.
    """

    _instances = {}

    def __new__(cls, name: str, log_file: Optional[Union[str, Path]] = None, level=logging.INFO):
        if name in cls._instances:
            return cls._instances[name]
        instance = super().__new__(cls)
        cls._instances[name] = instance
        return instance

    def __init__(self, name: str, log_file: Optional[Union[str, Path]] = None, level=logging.INFO):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self.name = name
        self.log_file = Path(log_file) if log_file else None
        self.level = level

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        # Remove existing handlers
        self.logger.handlers.clear()

        # Console handler with Rich
        console_handler = RichHandler(
            console=Console(),
            show_time=True,
            show_path=False,
            show_level=True,
            rich_tracebacks=True,
            markup=True,
        )
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(console_handler)

        # File handler (if log_file provided)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)

    def success(self, msg: str, *args, **kwargs):
        """Custom success level (using INFO with green color via Rich markup)"""
        self.logger.info(f"[bold green]✓[/bold green] {msg}", *args, **kwargs)

    def fail(self, msg: str, *args, **kwargs):
        """Custom fail level (using ERROR with red color via Rich markup)"""
        self.logger.error(f"[bold red]✗[/bold red] {msg}", *args, **kwargs)

    def section(self, title: str):
        """Print a section header with separators"""
        self.logger.info("")
        self.logger.info(f"[bold cyan]{'='*60}[/bold cyan]")
        self.logger.info(f"[bold cyan]{title.center(60)}[/bold cyan]")
        self.logger.info(f"[bold cyan]{'='*60}[/bold cyan]")
        self.logger.info("")

    def step(self, step_num: int, description: str):
        """Print a step header"""
        self.logger.info(f"[bold yellow]▶ STEP {step_num}:[/bold yellow] {description}")

    def progress(self, current: int, total: int, message: str = ""):
        """Print progress info"""
        percent = (current / total) * 100 if total > 0 else 0
        self.logger.info(f"[dim]Progress: {current}/{total} ({percent:.1f}%)[/dim] {message}")


# Convenience function to get logger instance
def get_logger(name: str, log_file: Optional[Union[str, Path]] = None, level=logging.INFO) -> CustomLogger:
    """Get or create a CustomLogger instance."""
    return CustomLogger(name, log_file, level)


# Default project logger (to be used throughout)
_default_logger = None


def setup_project_logger(log_file: Optional[Union[str, Path]] = None, level=logging.INFO) -> CustomLogger:
    """Setup the default project logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger("miniheroes", log_file, level)
    return _default_logger


def log() -> CustomLogger:
    """Get the default project logger."""
    if _default_logger is None:
        raise RuntimeError("Logger not initialized. Call setup_project_logger() first.")
    return _default_logger