from src.app import add


def test_addition() -> None:
    """Tests the add function with basic integer addition.

    Verifies that adding 2 and 3 returns the expected result of 5.

    Example:
        >>> test_addition()  # Runs assertion test

    """
    # arrange
    expected = 5
    # act
    actual = add(2, 3)
    # assert
    assert actual == expected
