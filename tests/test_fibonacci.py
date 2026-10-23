import pytest

from service.fibonacci import fibonacci_sequence


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, []),
        (1, [0]),
        (2, [0, 1]),
        (5, [0, 1, 1, 2, 3]),
        (10, [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]),
    ],
)
def test_small_numbers(n: int, expected: list[int]) -> None:
    assert fibonacci_sequence(n) == expected


def test_length_matches() -> None:
    assert len(fibonacci_sequence(1000)) == 1000


def test_each_number_is_the_sum_of_the_previous_two() -> None:
    seq = fibonacci_sequence(500)
    assert all(seq[i] == seq[i - 1] + seq[i - 2] for i in range(2, len(seq)))


def test_large_values_are_exact() -> None:
    assert fibonacci_sequence(101)[100] == 354224848179261915075


def test_negative() -> None:
    with pytest.raises(ValueError, match="n must not be negative, got -1"):
        fibonacci_sequence(-1)
