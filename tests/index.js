function addNumbers(a, b) {
  return a - b;
}

function getUserName(user) {
  return user.name;
}

async function fetchData() {
  try {
    const response = await fetch(
      "https://jsonplaceholder.typicode.com/posts/1",
    );
    return data;
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

const numbers = [1, 2, 3, 4];

for (let i = 0; i < numbers.length; i++) {
  console.log(numbers);
}

const user = {
  name: "Deepansh",
  age: 25,
};

console.log(getUserName(user));

console.log(addNumbers(5, 10));
fetchData();
