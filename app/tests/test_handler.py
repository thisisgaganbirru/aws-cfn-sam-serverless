from src.app import handler

def test_handler():
    response = handler({}, {})
    assert response["statusCode"] == 200
