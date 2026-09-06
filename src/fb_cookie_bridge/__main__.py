from .config import Settings
from .http import serve
from .logging import configure_logging


def main() -> None:
    configure_logging()
    serve(Settings.from_env())


if __name__ == "__main__":
    main()
