const api = 'http://localhost:3000';

const loginBtn = document.getElementById('loginBtn');
const userInput = document.getElementById('user');
const catalogList = document.getElementById('catalog');
const content = document.getElementById('content');
let token = '';

loginBtn.addEventListener('click', async () => {
  const username = userInput.value;
  const res = await fetch(api + '/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username })
  });
  const data = await res.json();
  token = data.token;
  content.style.display = 'block';
  loadCatalog();
});

async function loadCatalog() {
  const res = await fetch(api + '/api/inventory', {
    headers: { 'Authorization': 'Bearer ' + token }
  });
  const items = await res.json();
  catalogList.innerHTML = '';
  items.forEach(item => {
    const li = document.createElement('li');
    li.textContent = item.name;
    catalogList.appendChild(li);
  });
}

