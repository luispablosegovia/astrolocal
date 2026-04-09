# Contribuir a AstroLocal

¡Gracias por querer contribuir! 🔮

## Reglas de seguridad (obligatorias)

1. **Nunca interpolar strings en queries SQL.** Siempre usar parámetros (`?`).
2. **Todo input de usuario pasa por Pydantic** antes de llegar al core.
3. **No usar `eval()`, `exec()`, ni `pickle.loads()`** bajo ninguna circunstancia.
4. **No agregar URLs externas** al LLM client sin validación de localhost.
5. **No loguear PII** (nombres, fechas de nacimiento, coordenadas exactas).

## Setup de desarrollo

```bash
git clone https://github.com/TU-USUARIO/astrolocal.git
cd astrolocal
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Antes de hacer un PR

```bash
# Tests pasan
pytest tests/ -v

# Sin errores de lint
ruff check astrolocal/

# Sin issues de seguridad
bandit -r astrolocal/ -ll
```

## Estructura de commits

```
Add: nueva feature
Fix: bug fix
Sec: fix de seguridad
Docs: documentación
Refactor: refactoring sin cambio de comportamiento
Test: agregar o mejorar tests
```
