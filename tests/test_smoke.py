"""T03 環境煙霧測試：套件可安裝、可 import、版本可查。

不含資料檔案相依（data/ 不入 Git），資料讀檔檢查見 docs/LOCAL_ENVIRONMENT.md
與 outputs/local_env/ 的紀錄。
"""

import sys
from importlib.metadata import PackageNotFoundError, version

import aiot_price


def test_package_importable() -> None:
    assert aiot_price.__version__ == "0.1.0"


def test_required_dependencies_installed() -> None:
    for name in ("pandas", "numpy", "scikit-learn", "PyYAML", "requests", "jsonschema"):
        assert version(name), f"{name} 應已安裝"


def test_python_version_supported() -> None:
    assert sys.version_info >= (3, 10)


def test_missing_dependency_reports_not_found() -> None:
    try:
        version("definitely-not-a-real-package-xyz")
    except PackageNotFoundError:
        pass  # 預期行為
    else:  # pragma: no cover
        raise AssertionError("不存在的套件應回報 PackageNotFoundError")
