# Trading Bot v0.3 - Paquetes Independientes 🚀

## 🎯 **Nueva Arquitectura v0.3**

La versión **v0.3** introduce una **arquitectura de paquetes independientes** diseñada para deployment separado y escalabilidad microservicios.

### 📦 **Estructura de Paquetes**

```
v0_3/
├── shared/                          # 🔄 CÓDIGO COMPARTIDO
│   ├── domain/                      # Modelos y puertos de dominio hexagonal
│   ├── infrastructure/              # DI Container, adapters, servicios base
│   ├── logger.py                    # Sistema de logging centralizado
│   ├── settings.py                  # Configuración de entorno
│   ├── persistence.py              # Persistencia JSON unified
│   └── requirements.txt            # Dependencias compartidas
│
├── stm/                            # 📦 STM PAQUETE INDEPENDIENTE
│   ├── app.py                      # FastAPI application STM
│   ├── main.py                     # Entry point STM
│   ├── services/                   # Servicios Core STM
│   ├── routers/                    # API endpoints STM
│   ├── models/                     # Modelos específicos STM
│   ├── data/                       # Persistencia datos STM
│   └── requirements.txt            # Dependencias STM
│
└── server/                         # 📦 SERVER PAQUETE INDEPENDIENTE
    ├── app.py                      # FastAPI application Server
    ├── main.py                     # Entry point Server
    ├── services/                   # Servicios Core Server
    ├── routers/                    # API endpoints Server
    ├── strategies/                 # Configuraciones estrategias
    └── requirements.txt           # Dependencias Server
```

### ⚡ **Inicio Rápido**

```bash
# STM v0.3 - Synthetic Trading Manager
./start_stm_v3.sh

# Server v0.3 - Strategy Engine & API
./start_server_v3.sh
```

### 🔗 **Endpoints Principales**

#### STM v0.3 (Puerto 8100)

- `GET /health` - Health check
- `GET /sapi/v1/margin/positions` - Posiciones trading
- `GET /account/synth` - Cuenta sintética

#### Server v0.3 (Puerto 8200)

- `GET /health` - Health check
- `GET /strategies/` - Lista estrategias
- `GET /ws/status` - Estado WebSocket hexagonal
- `WebSocket /ws` - Conexión tiempo real

### 🏗️ **Arquitectura Hexagonal Completa**

- ✅ **Domain Models**: Entities, Value Objects, Aggregates
- ✅ **Application Services**: Casos de uso por dominio
- ✅ **Infrastructure Adapters**: Repositorios, servicios externos
- ✅ **DI Container**: Dependency injection centralizado
- ✅ **Ports & Adapters**: Interfaces desacopladas

### 📊 **Dominios Implementados**

| Dominio           | Estado  | Servicios Activos     |
| ----------------- | ------- | --------------------- |
| **Trading**       | ✅ 100% | Positions/Orders/Fees |
| **Account**       | ✅ 100% | Balance/Commission    |
| **Strategy**      | ✅ 100% | Indicators/Strategies |
| **Communication** | ✅ 100% | WebSocket Service     |

### 🚀 **Deployment Independiente**

Cada paquete puede deployarse por separado:

1. **STM**: Trading core + Binance integration
2. **Server**: Strategy engine + WebSocket frontend
3. **Comunicación**: HTTP API entre servicios

### 🐳 **Containerización**

```bash
# STM Container
docker build -f docker/stm/Dockerfile -t stm-v0.3 .

# Server Container
docker build -f docker/server/Dockerfile -t server-v0.3 .

# Orquestación completa
docker-compose -f docker/docker-compose.yml up
```

### 📈 **Escalabilidad**

- **STM**: Escalable horizontalmente (múltiples instancias)
- **Server**: Strategy engines independientes
- **Shared**: Código común sin duplicación

### 🔄 **Migración desde v0_2**

```bash
# Los scripts .sh automáticamente manejan:
# - Detección procesos v0_2/stm/v0_2/server
# - Liberación puertos conflictivos
# - Migración automática de datos
```

---

**Versión**: v0.3  
**Estado**: ✅ Production Ready  
**Arquitectura**: Hexagonal + Microservicios  
**Deployment**: Independiente por paquete
