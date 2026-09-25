"""굿포인트 애플리케이션 실행 진입점."""

if __package__:
    from .main_window import run
else:
    from src.main_window import run


if __name__ == "__main__":
    raise SystemExit(run())
