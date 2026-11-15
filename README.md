# Sistema de Registro Bancario BASA

Portal independiente de registro bancario interno integrado conceptualmente con Audit Intelligence USA.

## Inicio local

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Acceso inicial

- Usuario: `admin`
- Contraseña: `BASA_ADMIN_2026`

Cambiar la contraseña inicial antes de cualquier uso real.

## Persistencia

SQLite se crea automáticamente en `data/basa_banking_registry.db`.

## Producción

Este paquete es un núcleo de registro interno/prototipo. Un sistema bancario real requiere, entre otras cosas, autorización regulatoria, MFA, RBAC/segregación de funciones, cifrado, gestión de secretos, PostgreSQL administrado, backups, monitoreo, pruebas de seguridad, controles KYC/AML y conexiones únicamente mediante APIs autorizadas.

No contiene ni utiliza dominios, scripts, rastreadores, logos, credenciales o APIs de Banreservas.
