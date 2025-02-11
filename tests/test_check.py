from django.core.management import call_command

def test_check():
    call_command("check")  # This ensures Django’s admin checks run in tests
