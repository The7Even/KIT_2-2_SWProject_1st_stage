"""공통 JSON 저장소 접근 계층."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable


class JsonRepositoryError(Exception):
    """JSON 저장소 처리 중 발생하는 오류입니다."""


class JsonValidationError(JsonRepositoryError):
    """JSON 데이터 구조가 예상과 다를 때 발생하는 오류입니다."""


class JsonRepository:
    """JSON 파일을 안전하게 읽고 쓰는 저장소입니다."""

    def load(self, path: str | os.PathLike[str]) -> Any:
        file_path = Path(path)
        if not file_path.is_file():
            raise JsonRepositoryError(f"데이터 파일이 존재하지 않습니다: {file_path}")

        try:
            with file_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise JsonRepositoryError(
                f"JSON 형식이 올바르지 않습니다: {file_path}"
            ) from error
        except OSError as error:
            raise JsonRepositoryError(
                f"데이터 파일을 읽을 수 없습니다: {file_path}"
            ) from error

    def load_records(
        self,
        path: str | os.PathLike[str],
        required_fields: Iterable[str] = (),
    ) -> list[dict[str, Any]]:
        data = self.load(path)
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise JsonValidationError(f"배열 형태의 객체 목록이 필요합니다: {path}")

        required = set(required_fields)
        for index, record in enumerate(data):
            missing = required.difference(record)
            if missing:
                fields = ", ".join(sorted(missing))
                raise JsonValidationError(
                    f"{path}의 {index}번째 데이터에 필수 항목이 없습니다: {fields}"
                )
        return data

    def save(self, path: str | os.PathLike[str], data: Any) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=file_path.parent,
                prefix=f".{file_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(data, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, file_path)
        except (OSError, TypeError, ValueError) as error:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise JsonRepositoryError(
                f"데이터 파일을 저장할 수 없습니다: {file_path}"
            ) from error
