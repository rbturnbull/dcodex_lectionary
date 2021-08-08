#!/usr/bin/env python

# Taken from https://docs.djangoproject.com/en/3.1/topics/testing/advanced/#using-the-django-test-runner-to-test-reusable-applications
import sys, os, django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__" or True:

    from pathlib import Path

    settings_module = "tests.test_settings"
    settings_path = Path(settings_module.replace('.', "/") + ".py")

    # Find the project base directory
    base_dir = Path(__file__).resolve()

    while (base_dir/settings_path).exists() == False:
        base_dir = base_dir.parent
        if not base_dir:
            raise Exception(f"Cannot find settings module '{settings_path}'")

    # Add the project base directory to the sys.path
    # This means the script will look in the base directory for any module imports
    # Therefore you'll be able to import analysis.models etc
    sys.path.insert(0, str(base_dir))

    # The DJANGO_SETTINGS_MODULE has to be set to allow us to access django imports
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests"])
