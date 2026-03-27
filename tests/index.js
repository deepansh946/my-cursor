function addNumbers(a, b) {
  // Bug Fix 1: Corrected to add numbers instead of subtracting
  return a + b;
}

function getUserName(user) {
  return user.name;
}

async function fetchData() {
  try {
    const response = await fetch(
      "https://jsonplaceholder.typicode.com/posts/1",
    );
    // Bug Fix 2: Return the JSON data from the response
    return await response.json(); 
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

const numbers = [1, 2, 3, 4];

for (let i = 0; i < numbers.length; i++) {
  // Bug Fix 3: Log the current element of the array
  console.log(numbers[i]); 
}

const user = {
  name: "Deepansh",
  age: 25,
};

console.log(getUserName(user));

console.log(addNumbers(5, 10));
fetchData();
