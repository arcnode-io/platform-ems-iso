from src import config
from src.app import app
import logging


def main() -> None:
    """Execute the main entry point of the application.

    Load configuration, set up logging, and run the app with sample values.

    Example:
        >>> main()  # Loads config and runs app(1, 2)

    """
    cfg = config.load_config()
    config.setup_logger(cfg)
    logging.info(f"Running with: Config( {cfg} )")
    app(1, 2)


if __name__ == "__main__":
    main()
