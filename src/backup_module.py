"""JSON 데이터 백업 모듈."""

import shutil
from datetime import datetime
from pathlib import Path

from .json_repository import JsonRepository, JsonRepositoryError


class BackupModule:
    """변경된 JSON 파일을 타임스탬프가 붙은 폴더에 백업합니다."""

    def __init__(
        self,
        backup_dir: str | Path | None = None,
        repository: JsonRepository | None = None,
    ):
        self.backup_dir = Path(backup_dir) if backup_dir else (
            Path(__file__).parent / "data" / "backup"
        )
        self.repository = repository or JsonRepository()

    def backup(self, files: list[str]) -> bool:
        """유효한 JSON 파일을 백업하고, 실패 시 명시적으로 False를 반환합니다."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destination_dir = self.backup_dir / timestamp
        copied_files: list[Path] = []

        try:
            for file_name in files:
                source = Path(file_name)
                data = self.repository.load(source)
                destination = destination_dir / source.name
                self.repository.save(destination, data)
                copied_files.append(destination)
        except (JsonRepositoryError, OSError) as error:
            print(f"[오류] 백업 실패: {error}")
            if destination_dir.exists():
                shutil.rmtree(destination_dir)
            return False

        print(f"[안내] 백업 완료: {len(copied_files)}개 파일")
        return True
