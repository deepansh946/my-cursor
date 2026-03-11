function addNumbers(a, b) {
  return a + b;
}

function getUserName(user) {
  return user.name.toUpperCase();
}

async function fetchData() {
  const data = await fetch("https://jsonplaceholder.typicode.com/posts/1");
  const json = await data.json();
  console.log(json);
}

const numbers = [1, 2, 3, 4];

for (let i = 0; i < numbers.length; i++) {
  console.log(numbers[i]);
}

const user = {
  name: "Deepansh",
  age: 25,
};

console.log(getUserName(user));

addNumbers(5, 10);
fetchData();
