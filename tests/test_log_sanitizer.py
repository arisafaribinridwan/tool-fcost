from __future__ import annotations

from app.utils.log_sanitizer import sanitize_exception_message, sanitize_log_message


def test_sanitize_log_message_masks_workspace_path_email_and_long_number(tmp_path):
    workspace = tmp_path / "repo"
    nested = workspace / "outputs" / "hasil.xlsx"
    message = (
        f"Gagal baca {nested} untuk user tester@example.com dengan rekening 1234567890123456"
    )

    sanitized = sanitize_log_message(message, project_root=workspace)

    assert str(nested) not in sanitized
    assert "<outputs/hasil.xlsx>" in sanitized
    assert "te***@example.com" in sanitized
    assert "1234567890123456" not in sanitized
    assert sanitized.endswith("3456")


def test_sanitize_exception_message_truncates_long_multiline_payload(tmp_path):
    workspace = tmp_path / "repo"
    long_message = (str(workspace / "data.csv") + "\n") + ("baris-data " * 80)

    sanitized = sanitize_exception_message(long_message, project_root=workspace)

    assert "\n" not in sanitized
    assert len(sanitized) <= 400
    assert "[dipotong]" in sanitized
