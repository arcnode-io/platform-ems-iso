def add(a: int, b: int) -> int:
    """Add two integers together.

    Args:
        a: First integer to add
        b: Second integer to add

    Returns:
        Sum of the two integers

    Example:
        >>> add(2, 3)
        5

    """
    return a + b


def app(a: int, b: int) -> int:
    """Execute the main application function that adds two integers.

    Args:
        a: First integer to add
        b: Second integer to add

    Returns:
        Sum of the two integers via the add function

    Example:
        >>> app(5, 7)
        12

    """
    return add(a, b)
