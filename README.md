# IARecycla

Plataforma de gestión de reciclaje de teléfonos móviles.

## Estructura
- `docs/` Documentación de requisitos y arquitectura.
- `backend/` API REST construida con Express + json-server.
- `frontend/` Prototipo simple de la aplicación web.

## Uso Rápido
1. Instalar dependencias:
   ```bash
   npm install
   ```
2. Ejecutar el servidor:
   ```bash
   node backend/server.js
   ```
3. Abrir `frontend/index.html` en el navegador para probar la interfaz.

Este proyecto es un MVP inicial y puede expandirse con pruebas, estilos y persistencia real.

## Flask Web Application

Se agregó una aplicación web en `webapp/` basada en Flask que implementa el flujo de reciclaje de manera sencilla. Para probarla:

```bash
pip install -r webapp/requirements.txt
python webapp/app.py
```
Esto funcionará en Windows o Linux porque las rutas internas usan `os.path.join`. La interfaz incluye formularios para registrar teléfonos, componentes y más.

La API sigue disponible y expone endpoints protegidos con JWT para gestionar usuarios, teléfonos, componentes, proveedores y pedidos.
