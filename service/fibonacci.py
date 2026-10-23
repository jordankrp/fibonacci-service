# Upper bound on how many numbers a single request may ask for. For n=1000 we have around 105,000 digits,
# which keeps the response around 100 KB (assuming 1 digit = 1 byte in plain ASCII). Without a cap,
# a single request for a large n would tie up a worker and produce a response of unbounded size.
MAX_N = 1000


def fibonacci_sequence(n: int) -> list[int]:
    """Returns the first n Fibonacci numbers, starting from 0.
    e.g for n=5 returns [0, 1, 1, 2, 3]
    """
    if n < 0:
        raise ValueError(f"n must not be negative, got {n}")

    result: list[int] = []
    a, b = 0, 1
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result
