# 🔮 AstroLocal

**Tu astrólogo personal con IA local. 100% privado, 100% offline, 0% nube.**

AstroLocal combina [Kerykeion](https://github.com/g-battaglia/kerykeion) (motor de cálculos astrológicos) con un LLM local (vía [Ollama](https://ollama.com)) para generar interpretaciones astrológicas profundas y personalizadas sin que tus datos salgan de tu máquina.

---

## ✨ Features

- **Carta natal** completa con interpretación personalizada por IA
- **Tránsitos diarios** — cómo te afectan los planetas hoy
- **Sinastría** — compatibilidad entre dos personas
- **Detección automática** de stelliums, Gran Trígono, T-Cuadrada
- **Streaming** — la interpretación aparece en tiempo real
- **Perfiles** — guardá múltiples personas y consultá cuando quieras
- **Historial** — todas las lecturas se guardan en SQLite
- **CLI hermosa** con [Rich](https://github.com/Textualize/rich)

## 🔒 Privacidad y Seguridad

- Todo corre en tu máquina. Cero datos enviados a la nube
- Logs con PII redactada por defecto
- Input validado con Pydantic (inyección SQL imposible)
- LLM solo se conecta a localhost/red privada
- Rate limiting, timeouts, y retries con backoff
- CI con Bandit (análisis de seguridad) y Safety (vulnerabilidades en deps)

Ver [SECURITY.md](SECURITY.md) para detalles completos.

## 📋 Requisitos

- **Python 3.11+**
- **Ollama** instalado y corriendo
- **8-24 GB de RAM** dependiendo del modelo LLM
- macOS (Apple Silicon recomendado), Linux, o Windows con WSL

## 🚀 Instalación

```bash
# 1. Instalar Ollama
brew install ollama  # macOS
# o ver https://ollama.com para otros OS

# 2. Bajar un modelo (elegí uno)
ollama pull qwen2.5:14b      # Recomendado: mejor calidad (~10 GB RAM)
ollama pull llama3.2:8b       # Alternativa: más rápido (~6 GB RAM)

# 3. Clonar e instalar AstroLocal
git clone https://github.com/luispablosegovia/astrolocal.git
cd astrolocal
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 4. (Opcional) Copiar configuración
mkdir -p ~/.astrolocal
cp config.example.toml ~/.astrolocal/config.toml
```

## 📖 Uso

### Verificar que todo funciona

```bash
astrolocal doctor
```

### Carta natal

```bash
astrolocal natal "Juan" 1990 3 15 14 30 "Buenos Aires" AR
```

Esto va a:
1. Calcular la carta natal con Kerykeion
2. Mostrar un resumen de posiciones planetarias
3. Generar una interpretación completa con el LLM local
4. Guardar el perfil y la lectura automáticamente

### Tránsitos de hoy

```bash
astrolocal transits "Juan"
```

### Sinastría

```bash
# Primero creá ambos perfiles con 'natal', después:
astrolocal synastry "Juan" "María"
```

### Gestionar perfiles

```bash
astrolocal profile list
astrolocal profile delete 3
```

### Opciones útiles

```bash
# Sin streaming (espera la respuesta completa)
astrolocal natal "Juan" 1990 3 15 14 30 "Buenos Aires" AR --no-stream

# Sin guardar en la base de datos
astrolocal natal "Juan" 1990 3 15 14 30 "Buenos Aires" AR --no-save

# Config personalizada
astrolocal --config ./mi-config.toml natal ...
```

## ⚙️ Configuración

AstroLocal busca la configuración en `~/.astrolocal/config.toml`. Ver [config.example.toml](config.example.toml) para todas las opciones.

Variables de entorno (sobreescriben el archivo):

| Variable | Descripción |
|---|---|
| `ASTROLOCAL_LLM_MODEL` | Modelo a usar |
| `ASTROLOCAL_LLM_BASE_URL` | URL del servidor LLM |
| `ASTROLOCAL_LLM_PROVIDER` | `ollama`, `mlx`, o `openai_compat` |
| `ASTROLOCAL_DB_PATH` | Path a la base de datos |
| `ASTROLOCAL_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## 🏗️ Arquitectura

```
Usuario → CLI (Click + Rich)
            ↓
        Orquestador (interpreter.py)
        ↙                ↘
  Kerykeion            LLM Local (Ollama)
  (cálculos)           (interpretación)
        ↘                ↙
        Prompt Engine
        (templates + knowledge base)
            ↓
        SQLite (persistencia)
```

## 🧪 Desarrollo

```bash
# Instalar dependencias de desarrollo
pip install -e ".[dev]"

# Tests
pytest tests/ -v

# Linting
ruff check astrolocal/
ruff format astrolocal/

# Análisis de seguridad
bandit -r astrolocal/ -ll

# Pre-commit hooks
pre-commit install
```

## 🤝 Contribuir

1. Fork del repo
2. Creá una branch (`git checkout -b feature/mi-feature`)
3. Commiteá tus cambios (`git commit -m 'Add: mi feature'`)
4. Push a la branch (`git push origin feature/mi-feature`)
5. Abrí un Pull Request

Por favor leé [SECURITY.md](SECURITY.md) antes de contribuir.

## 📄 Licencia

MIT — ver [LICENSE](LICENSE).

## 🙏 Créditos

- [Kerykeion](https://github.com/g-battaglia/kerykeion) por el motor astrológico
- [Ollama](https://ollama.com) por hacer LLMs locales accesibles
- [Rich](https://github.com/Textualize/rich) por la hermosa CLI
- [Pydantic](https://docs.pydantic.dev) por la validación de datos
