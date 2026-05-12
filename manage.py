#!/usr/bin/env python
"""Django upravljalska skripta za BookMatch."""
import os
import sys


def main():
    """Zažene administrativna opravila."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmatch.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django ni nameščen. Najprej poženi 'pip install -r requirements.txt'."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
