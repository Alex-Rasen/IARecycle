const express = require('express');
const fs = require('fs');
const path = require('path');
const jwt = require('jsonwebtoken');

const app = express();
const DB_PATH = path.join(__dirname, '../data/db.json');

app.use(express.json());

// Utilidades simples para leer y escribir la base JSON
function readDB() {
  const raw = fs.readFileSync(DB_PATH);
  return JSON.parse(raw);
}

function writeDB(data) {
  fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2));
}

// Login de demostración
app.post('/login', (req, res) => {
  const { username } = req.body;
  if (!username) return res.status(400).json({ error: 'username required' });
  const token = jwt.sign({ username }, 'secret', { expiresIn: '1h' });
  res.json({ token });
});

// Middleware de autenticación
app.use((req, res, next) => {
  if (req.path === '/login') return next();
  const token = (req.headers.authorization || '').replace('Bearer ', '');
  if (!token) return res.status(401).json({ error: 'Token required' });
  try {
    jwt.verify(token, 'secret');
    next();
  } catch {
    res.status(401).json({ error: 'Invalid token' });
  }
});

// Endpoints CRUD basicos
app.get('/api/:collection', (req, res) => {
  const db = readDB();
  const data = db[req.params.collection] || [];
  res.json(data);
});

app.post('/api/:collection', (req, res) => {
  const db = readDB();
  const item = req.body;
  const collection = db[req.params.collection] || [];
  item.id = Date.now();
  collection.push(item);
  db[req.params.collection] = collection;
  writeDB(db);
  res.status(201).json(item);
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
