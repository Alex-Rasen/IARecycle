# IARecycla

Plataforma de gestión de reciclaje de teléfonos móviles.


## Flask Web Application

Se agregó una aplicación web en `webapp/` basada en Flask que implementa el flujo de reciclaje de manera sencilla. Para probarla:

```bash
pip install -r webapp/requirements.txt
python webapp/app.py
```


Esto funcionará en Windows o Linux porque las rutas internas usan `os.path.join`. La interfaz incluye formularios para registrar teléfonos, componentes y más.

La API sigue disponible y expone endpoints protegidos con JWT para gestionar usuarios, teléfonos, componentes, proveedores y pedidos.


