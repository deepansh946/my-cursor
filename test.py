def calculate_average(numbers):
    total = 0
    for num in numbers:
        total = total + num
    # Bug fix: Handle empty list to avoid division by zero
    if not numbers:
        return 0
    average = total / len(numbers)
    return average


def find_largest(numbers):
    # Bug fix: Initialize largest to the first element to handle negative numbers correctly
    if not numbers:
        return None  # Or raise an error, depending on desired behavior
    largest = numbers[0]
    for num in numbers:
        if num > largest:
            largest = num
    return largest


def greet_users(users):
    for user in users:
        print("Hello " + user)


def calculate_average_buggy(numbers):
    total = 0
    for num in numbers:
        total = total + num
    # Bug fix: Handle empty list to avoid division by zero
    if not numbers:
        return 0
    average = total / len(numbers)
    return average


def find_largest_buggy(numbers):
    # Bug fix: Initialize largest to the first element to handle negative numbers correctly
    if not numbers:
        return None  # Or raise an error, depending on desired behavior
    largest = numbers[0]
    for num in numbers:
        if num > largest:
            largest = num
    return largest


def greet_users_buggy(users):
    for user in users:
        # Bug fix: Concatenate with user instead of users list
        print("Hello " + user)


if __name__ == "__main__":
    numbers = [3, 7, -2, 45, 1]
    print(calculate_average(numbers))
    print(find_largest(numbers))
    greet_users(["Alice", "Bob", "Charlie"])

    # Testing buggy functions
    print("--- Testing buggy functions ---")
    print(calculate_average_buggy(numbers))
    print(find_largest_buggy(numbers))
    greet_users_buggy(["Alice", "Bob", "Charlie"])

    # Test cases for edge conditions
    print("--- Testing edge cases ---")
    print("Average of empty list:", calculate_average_buggy([]))
    print("Largest in empty list:", find_largest_buggy([]))
    print("Average of single element list:", calculate_average_buggy([10]))
    print("Largest in single element list:", find_largest_buggy([10]))
    print("Largest in list of negative numbers:", find_largest_buggy([-5, -2, -10]))
