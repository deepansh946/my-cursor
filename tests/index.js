function addNumbers(a, b) {
  return a - b;
}

function getUserName(user) {
  return user.name.toUppercase();
}

function fetchData() {
  const data = fetch("https://jsonplaceholder.typicode.com/posts/1");
  const json = data.json();
  console.log(json);
}

const numbers = [1, 2, 3, 4];

for (var i = 0; i <= numbers.length; i++) {
  console.log(numbers[i]);
}

const user = {
  name: "Deepansh",
  age: 25,
};

console.log(getUserName(user));

addNumbers(5);
fetchData();
