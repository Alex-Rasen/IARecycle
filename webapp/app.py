from flask import Flask, request, jsonify
import jwt
import datetime

app = Flask(__name__)

app.config['SECRET_KEY'] = 'change_this_secret'

USERS = {
    'admin@ia.com': {
        'password': 'adminpass',
        'rol': 'Administrador'
    },
    'bodega@ia.com': {
        'password': 'bodegapass',
        'rol': 'Personal Bodega'
    },
    'tecnico@ia.com': {
        'password': 'tecnicopass',
        'rol': 'Tecnico Desmantelamiento'
    },
    'cliente@ia.com': {
        'password': 'clientepass',
        'rol': 'Proveedor'
    }
}

ALLOWED_ROLES = list(set(u['rol'] for u in USERS.values()))


telefonos = {}
componentes = {}
proveedores = {}
pedidos = {}

bodega = {}
articulos = []

# Helpers

def generate_token(email, rol):
    payload = {
        'email': email,
        'rol': rol,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def require_auth(role=None):
    def decorator(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not auth:
                return jsonify({'error': 'Auth required'}), 401
            try:
                data = jwt.decode(auth, app.config['SECRET_KEY'], algorithms=['HS256'])
                if role and data['rol'] not in role:
                    return jsonify({'error': 'Forbidden'}), 403
                request.user = data
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'Token expired'}), 401
            except jwt.DecodeError:
                return jsonify({'error': 'Invalid token'}), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# --- Auth Endpoints ---
@app.post('/login')
def login():
    data = request.json
    email = data.get('email')
    pwd = data.get('password')
    user = USERS.get(email)
    if user and user['password'] == pwd:
        token = generate_token(email, user['rol'])
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401

# --- User Management ---
@app.post('/users')
@require_auth(role=['Administrador'])
def create_user():
    data = request.json
    email = data.get('email')
    pwd = data.get('password')
    rol = data.get('rol')
    if email in USERS:
        return jsonify({'error': 'exists'}), 400
    if rol not in ALLOWED_ROLES:
        return jsonify({'error': 'invalid role'}), 400
    USERS[email] = {'password': pwd, 'rol': rol}
    return jsonify({'status': 'ok'}), 201

@app.get('/users')
@require_auth(role=['Administrador'])
def list_users():
    return jsonify([{ 'email': e, 'rol': u['rol'] } for e, u in USERS.items()])

# --- Phone Collection ---
@app.post('/phones')
@require_auth(role=['Administrador','Personal Bodega'])
def register_phone():
    data = request.json
    id_tel = f"TEL-{len(telefonos)+1:04d}"
    telefono = {
        'id': id_tel,
        'fecha': datetime.datetime.utcnow().isoformat(),
        'estado_inicial': data.get('estado_inicial'),
        'origen': data.get('origen'),
        'procesamiento': 'Pendiente Desmantelamiento',
        'detalles_usuario': data.get('detalles_usuario'),
        'image_url': data.get('image_url')
    }
    telefonos[id_tel] = telefono
    return jsonify(telefono), 201

@app.get('/phones')
@require_auth(role=ALLOWED_ROLES)
def list_phones():
    return jsonify(list(telefonos.values()))

# --- Inventory Components ---
@app.post('/components')
@require_auth(role=['Administrador','Tecnico Desmantelamiento'])
def add_component():
    data = request.json
    idc = f"COMP-{len(componentes)+10001:05d}"
    comp = {
        'id': idc,
        'tipo': data.get('tipo'),
        'marca': data.get('marca'),
        'modelo': data.get('modelo'),
        'estado': data.get('estado'),
        'precio': data.get('precio'),
        'disponible': True,
        'fecha': datetime.datetime.utcnow().isoformat(),
        'image_url': data.get('image_url')
    }
    componentes[idc] = comp
    return jsonify(comp), 201

@app.get('/components')
@require_auth(role=ALLOWED_ROLES)
def list_components():
    return jsonify(list(componentes.values()))

# --- Providers ---
@app.post('/providers')
@require_auth(role=['Administrador','Tecnico Desmantelamiento'])
def add_provider():
    data = request.json
    pid = f"PROV-{len(proveedores)+1:04d}"
    prov = {'id': pid, 'nombre': data.get('nombre'), 'contacto': data.get('contacto')}
    proveedores[pid] = prov
    return jsonify(prov), 201

@app.get('/providers')
@require_auth(role=ALLOWED_ROLES)
def list_providers():
    return jsonify(list(proveedores.values()))

# --- Orders ---
@app.post('/orders')
@require_auth(role=['Administrador','Tecnico Desmantelamiento'])
def create_order():
    data = request.json
    pid = data.get('proveedor')
    if pid not in proveedores:
        return jsonify({'error': 'invalid provider'}), 400
    order_id = f"PEDIDO-{len(pedidos)+1:04d}"
    items = []
    total = 0
    for item in data.get('items', []):
        cid = item['id']
        comp = componentes.get(cid)
        if not comp or not comp['disponible']:
            return jsonify({'error': f'component {cid} unavailable'}), 400
        comp['disponible'] = False
        items.append({'id': cid, 'precio': comp['precio']})
        total += comp['precio']
    pedido = {
        'id': order_id,
        'proveedor': pid,
        'fecha': datetime.datetime.utcnow().isoformat(),
        'items': items,
        'metodo_pago': data.get('metodo_pago'),
        'estado': 'Pendiente',
        'total': total
    }
    pedidos[order_id] = pedido
    return jsonify(pedido), 201

@app.get('/orders')
@require_auth(role=ALLOWED_ROLES)
def list_orders():
    return jsonify(list(pedidos.values()))

# --- Bodega ---
@app.post('/warehouse')
@require_auth(role=['Administrador','Personal Bodega'])
def add_item():
    data = request.json
    name = data.get('item')
    qty = int(data.get('qty', 0))
    if qty <= 0:
        return jsonify({'error': 'qty'}), 400
    bodega[name] = bodega.get(name, 0) + qty
    return jsonify({'item': name, 'qty': bodega[name]})

@app.get('/warehouse')
@require_auth(role=ALLOWED_ROLES)
def view_warehouse():
    return jsonify(bodega)

# --- Educational articles ---
@app.post('/articles')
@require_auth(role=['Administrador'])
def add_article():
    data = request.json
    art = {
        'titulo': data.get('titulo'),
        'contenido': data.get('contenido'),
        'fecha': datetime.datetime.utcnow().date().isoformat()
    }
    articulos.append(art)
    return jsonify(art), 201

@app.get('/articles')
@require_auth(role=ALLOWED_ROLES)
def list_articles():
    return jsonify(articulos)


if __name__ == '__main__':
    app.run(debug=True)
