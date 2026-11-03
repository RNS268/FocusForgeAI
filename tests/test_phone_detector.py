from core.phone_detector import PhoneDetector


def test_phone_detector_reports_unavailable_when_no_model_is_installed() -> None:
    detector = PhoneDetector(model_path="models/does_not_exist.pt")
    assert detector.available is False or detector.error_message
