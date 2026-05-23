from src.app import app


class TestIntegration:
    """Integration tests for the application."""

    def test_app(self) -> None:
        """Test the main app function with basic addition."""
        # arrange
        expected = 3
        # act
        actual = app(1, 2)
        # assert
        assert actual == expected
