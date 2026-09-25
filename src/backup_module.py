"""JSON 데이터 백업 모듈."""

import shutil
from datetime import datetime
from pathlib import Path

from .json_repository import JsonRepository, JsonRepositoryError
from .app_logging import logger


class BackupModule:
    """변경된 JSON 파일을 백업하고 최근 백업만 보관합니다."""

    MAX_BACKUPS = 5

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

        try:
            self._prune_old_backups()
        except OSError as error:
            print(f"[오류] 오래된 백업 정리 실패: {error}")
            return False

        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[안내] 백업 완료 ({completed_at}): "
            f"{len(copied_files)}개 파일"
        )
        logger.info("backup_completed files=%s", len(copied_files))
        return True

    def load_latest_backup(self, file_name: str | Path):
        """파일의 최신 백업 데이터를 반환하고 없으면 None을 반환합니다."""
        target_name = Path(file_name).name
        if not self.backup_dir.is_dir():
            return None

        backup_files = sorted(
            (
                path / target_name
                for path in self.backup_dir.iterdir()
                if path.is_dir() and (path / target_name).is_file()
            ),
            key=lambda path: path.parent.name,
            reverse=True,
        )
        for backup_file in backup_files:
            try:
                return self.repository.load(backup_file)
            except JsonRepositoryError as error:
                print(f"[오류] 백업 데이터 로드 실패: {backup_file} ({error})")
        return None

    def restore_latest_backup(self, file_name: str | Path) -> bool:
        """최신 백업을 원본 경로에 원자적으로 복원합니다."""
        target_path = Path(file_name)
        backup_data = self.load_latest_backup(target_path)
        if backup_data is None:
            return False
        try:
            self.repository.save(target_path, backup_data)
        except JsonRepositoryError as error:
            print(f"[오류] 백업 복원 실패: {target_path} ({error})")
            return False
        return True

    def load_records_with_backup(
        self,
        file_name: str | Path,
        required_fields: tuple[str, ...],
    ) -> list[dict]:
        try:
            return self.repository.load_records(file_name, required_fields)
        except JsonRepositoryError as error:
            print(f"[오류] 데이터 로드 실패: {error}")
            if Path(file_name).parent.resolve() != self.backup_dir.parent.resolve():
                return []
            backup_data = self.load_latest_backup(file_name)
            if not isinstance(backup_data, list) or any(
                not isinstance(item, dict)
                or any(field not in item for field in required_fields)
                for item in backup_data
            ):
                return []
            if not self.restore_latest_backup(file_name):
                return []
            try:
                return self.repository.load_records(file_name, required_fields)
            except JsonRepositoryError:
                return []

    def _prune_old_backups(self) -> None:
        """각 파일별 최신 백업 5개만 남기고 오래된 파일을 삭제합니다."""
        if not self.backup_dir.is_dir():
            return

        file_names = {
            backup_file.name
            for backup_dir in self.backup_dir.iterdir()
            if backup_dir.is_dir()
            for backup_file in backup_dir.glob("*.json")
        }
        for file_name in file_names:
            backup_files = sorted(
                (
                    path / file_name
                    for path in self.backup_dir.iterdir()
                    if path.is_dir() and (path / file_name).is_file()
                ),
                key=lambda path: path.parent.name,
                reverse=True,
            )
            for old_backup_file in backup_files[self.MAX_BACKUPS:]:
                old_backup_file.unlink()

        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir() and not any(backup_dir.iterdir()):
                backup_dir.rmdir()
