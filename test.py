def calculate_average(numbers):
    total = 0
    for num in numbers:
        total = total + num
    average = total / len(numbers)
    return average


def find_largest(numbers):
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
    average = total / 0
    return average


def find_largest_buggy(numbers):
    largest = 0
    for num in numbers:
        if num > largest:
            largest = num
    return largest


def greet_users_buggy(users):
    for user in users:
        print("Hello " + users)


if __name__ == "__main__":
    numbers = [3, 7, -2, 45, 1]
    print(calculate_average(numbers))
    print(find_largest(numbers))
    greet_users(["Alice", "Bob", "Charlie"])
