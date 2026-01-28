"""Output formatters for structured and human-readable CLI output."""

import json
from dataclasses import asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from helixops.cli.models import OutputFormat, CLIResult


class OutputFormatter:
    """Formats CLI output in various formats."""

    @staticmethod
    def format_result(
        result: CLIResult,
        format_type: OutputFormat,
    ) -> str:
        """Format a CLI result for output.

        Args:
            result: CLIResult to format
            format_type: Desired output format

        Returns:
            Formatted output string
        """
        if format_type == OutputFormat.JSON:
            return OutputFormatter._format_json(result)
        elif format_type == OutputFormat.YAML:
            return OutputFormatter._format_yaml(result)
        else:
            return OutputFormatter._format_text(result)

    @staticmethod
    def _format_json(result: CLIResult) -> str:
        """Format result as JSON.

        Args:
            result: CLIResult to format

        Returns:
            JSON string
        """
        output = {
            "success": result.success,
            "message": result.message,
            "exit_code": result.exit_code,
        }

        if result.data is not None:
            if isinstance(result.data, dict):
                output["data"] = result.data
            elif hasattr(result.data, "__dataclass_fields__"):
                output["data"] = asdict(result.data)
            elif isinstance(result.data, list):
                output["data"] = [
                    asdict(item) if hasattr(item, "__dataclass_fields__") else item
                    for item in result.data
                ]
            else:
                output["data"] = result.data

        if result.errors:
            output["errors"] = result.errors

        return json.dumps(output, indent=2, default=str)

    @staticmethod
    def _format_text(result: CLIResult) -> str:
        """Format result as plain text.

        Args:
            result: CLIResult to format

        Returns:
            Plain text string
        """
        lines = []

        if result.message:
            status = "✓" if result.success else "✗"
            lines.append(f"{status} {result.message}")

        if result.errors:
            lines.append("Errors:")
            for error in result.errors:
                lines.append(f"  {error}")

        if result.data is not None:
            if isinstance(result.data, dict):
                lines.append(json.dumps(result.data, indent=2, default=str))
            elif hasattr(result.data, "__dataclass_fields__"):
                lines.append(OutputFormatter._format_dataclass(result.data))
            else:
                lines.append(str(result.data))

        return "\n".join(lines)

    @staticmethod
    def _format_yaml(result: CLIResult) -> str:
        """Format result as YAML.

        Args:
            result: CLIResult to format

        Returns:
            YAML-like string
        """
        lines = [
            f"success: {str(result.success).lower()}",
            f"message: {result.message}",
            f"exit_code: {result.exit_code}",
        ]

        if result.errors:
            lines.append("errors:")
            for error in result.errors:
                lines.append(f"  - {error}")

        if result.data is not None:
            lines.append("data:")
            if isinstance(result.data, dict):
                for key, value in result.data.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append(f"  {result.data}")

        return "\n".join(lines)

    @staticmethod
    def _format_dataclass(obj: Any) -> str:
        """Format a dataclass object as text.

        Args:
            obj: Dataclass instance

        Returns:
            Formatted string
        """
        lines = []
        for field_name, field_value in asdict(obj).items():
            if field_value is not None:
                lines.append(f"{field_name}: {field_value}")
        return "\n".join(lines)


class ExitCodeManager:
    """Manages exit codes for CLI commands."""

    SUCCESS = 0
    VALIDATION_ERROR = 1
    RUNTIME_ERROR = 1
    FILE_NOT_FOUND = 2
    INVALID_ARGUMENT = 3
    NOT_FOUND = 4

    @staticmethod
    def get_code(error_type: str) -> int:
        """Get exit code for error type.

        Args:
            error_type: Type of error

        Returns:
            Exit code
        """
        code_map = {
            "validation": ExitCodeManager.VALIDATION_ERROR,
            "runtime": ExitCodeManager.RUNTIME_ERROR,
            "file_not_found": ExitCodeManager.FILE_NOT_FOUND,
            "invalid_argument": ExitCodeManager.INVALID_ARGUMENT,
            "not_found": ExitCodeManager.NOT_FOUND,
        }
        return code_map.get(error_type, ExitCodeManager.RUNTIME_ERROR)


class ErrorFormatter:
    """Formats error messages for CLI output."""

    @staticmethod
    def format_error(
        message: str,
        error_type: str = "runtime",
        details: Optional[List[str]] = None,
        format_type: OutputFormat = OutputFormat.TEXT,
    ) -> str:
        """Format an error message.

        Args:
            message: Error message
            error_type: Type of error
            details: Additional error details
            format_type: Output format

        Returns:
            Formatted error message
        """
        if details is None:
            details = []

        if format_type == OutputFormat.JSON:
            error_obj = {
                "error": True,
                "message": message,
                "type": error_type,
                "details": details,
            }
            return json.dumps(error_obj, indent=2)
        else:
            lines = [f"✗ {message}"]
            if details:
                for detail in details:
                    lines.append(f"  • {detail}")
            return "\n".join(lines)


class SuccessFormatter:
    """Formats success messages for CLI output."""

    @staticmethod
    def format_success(
        message: str,
        data: Optional[Dict] = None,
        format_type: OutputFormat = OutputFormat.TEXT,
    ) -> str:
        """Format a success message.

        Args:
            message: Success message
            data: Optional data to include
            format_type: Output format

        Returns:
            Formatted success message
        """
        if format_type == OutputFormat.JSON:
            success_obj = {
                "success": True,
                "message": message,
            }
            if data:
                success_obj["data"] = data
            return json.dumps(success_obj, indent=2)
        else:
            lines = [f"✓ {message}"]
            if data:
                lines.append(json.dumps(data, indent=2, default=str))
            return "\n".join(lines)
