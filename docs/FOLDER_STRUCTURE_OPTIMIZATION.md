# Folder Structure Optimization Proposal

## Current Structure Analysis

### Current Issues
1. **Root file clutter**: Multiple Python scripts at root level (`run.py`, `check_cw_data.py`, `fetch_us_indices.py`, etc.)
2. **Scattered configs**: Config files in `configs/` but also `.env` at root
3. **Mixed concerns**: Scripts, tools, and main application logic not clearly separated
4. **Module organization**: Backend modules could be better organized by domain
5. **Frontend/backend separation**: Could be clearer

### Current Structure
```
Finvista/
├── .agents/
├── .github/
├── alembic/
├── configs/
├── data/
├── docs/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── app/
│   │   ├── auth/
│   │   ├── components/
│   │   ├── features/
│   │   ├── i18n/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── styles/
│   │   └── test/
├── logs/
├── notebooks/
├── prompts/
├── scripts/
├── src/
│   ├── api/
│   ├── core/
│   ├── infra/
│   └── modules/
├── tests/
├── run.py
├── check_cw_data.py
├── fetch_us_indices.py
├── reingest_broken_cw.py
├── reingest_phase2.py
└── [other root files]
```

---

## Industry Best Practices

### Reference: Modern Fintech/Trading Platforms

**1. Robinhood/TradingView Style (Monorepo with Clear Separation)**
```
project/
├── apps/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── domain/
│   │   │   ├── infrastructure/
│   │   │   └── services/
│   │   ├── tests/
│   │   └── main.py
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── features/
│   │   │   ├── hooks/
│   │   │   ├── services/
│   │   │   └── utils/
│   │   └── public/
│   └── worker/
├── packages/
│   ├── shared/
│   └── types/
├── scripts/
├── tools/
├── docs/
└── config/
```

**2. Binance/Coinbase Style (Microservices-Ready)**
```
project/
├── services/
│   ├── market-data/
│   ├── trading/
│   ├── portfolio/
│   ├── analytics/
│   └── auth/
├── shared/
│   ├── database/
│   ├── messaging/
│   └── utils/
├── frontend/
├── infrastructure/
│   ├── monitoring/
│   ├── logging/
│   └── deployment/
├── scripts/
└── docs/
```

**3. FastAPI/React Best Practices (Domain-Driven)**
```
project/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── domain/
│   │   │   ├── market/
│   │   │   ├── portfolio/
│   │   │   ├── warrants/
│   │   │   └── analytics/
│   │   ├── infrastructure/
│   │   └── services/
│   ├── tests/
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── utils/
│   └── public/
├── scripts/
├── tools/
├── docs/
└── config/
```

---

## Proposed Optimized Structure

### Option 1: Domain-Driven Monorepo (Recommended for Current Scale)

```
Finvista/
├── apps/
│   ├── backend/
│   │   ├── alembic/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── routes/
│   │   │   │   ├── dependencies/
│   │   │   │   └── middleware/
│   │   │   ├── core/
│   │   │   │   ├── config/
│   │   │   │   ├── database/
│   │   │   │   ├── security/
│   │   │   │   └── logging/
│   │   │   ├── domain/
│   │   │   │   ├── market/
│   │   │   │   │   ├── models/
│   │   │   │   │   ├── services/
│   │   │   │   │   └── repositories/
│   │   │   │   ├── portfolio/
│   │   │   │   │   ├── models/
│   │   │   │   │   ├── services/
│   │   │   │   │   └── repositories/
│   │   │   │   ├── warrants/
│   │   │   │   │   ├── models/
│   │   │   │   │   ├── services/
│   │   │   │   │   └── repositories/
│   │   │   │   ├── analytics/
│   │   │   │   │   ├── regime/
│   │   │   │   │   ├── credit/
│   │   │   │   │   └── backtest/
│   │   │   │   └── data/
│   │   │   │       ├── scrapers/
│   │   │   │       ├── processors/
│   │   │   │       └── validators/
│   │   │   ├── infrastructure/
│   │   │   │   ├── scrapers/
│   │   │   │   ├── external_apis/
│   │   │   │   ├── cache/
│   │   │   │   ├── messaging/
│   │   │   │   └── storage/
│   │   │   └── services/
│   │   │       ├── scheduler/
│   │   │       ├── websocket/
│   │   │       └── monitoring/
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── e2e/
│   │   ├── scripts/
│   │   │   ├── data/
│   │   │   ├── maintenance/
│   │   │   └── deployment/
│   │   ├── main.py
│   │   └── pyproject.toml
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── providers/
│   │   │   │   ├── contexts/
│   │   │   │   └── hooks/
│   │   │   ├── components/
│   │   │   │   ├── ui/
│   │   │   │   ├── charts/
│   │   │   │   ├── tables/
│   │   │   │   └── layout/
│   │   │   ├── features/
│   │   │   │   ├── home/
│   │   │   │   ├── portfolio/
│   │   │   │   ├── market/
│   │   │   │   ├── warrants/
│   │   │   │   └── analytics/
│   │   │   ├── pages/
│   │   │   ├── services/
│   │   │   │   ├── api/
│   │   │   │   └── hooks/
│   │   │   ├── lib/
│   │   │   │   ├── utils/
│   │   │   │   ├── formatters/
│   │   │   │   └── constants/
│   │   │   ├── styles/
│   │   │   ├── i18n/
│   │   │   └── types/
│   │   ├── public/
│   │   ├── tests/
│   │   ├── package.json
│   │   └── vite.config.js
│   └── shared/
│       ├── types/
│       ├── constants/
│       └── utils/
├── tools/
│   ├── development/
│   ├── deployment/
│   └── monitoring/
├── scripts/
│   ├── setup/
│   ├── migration/
│   └── backup/
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── guides/
│   └── reference/
├── config/
│   ├── development/
│   ├── production/
│   └── staging/
├── data/
│   ├── raw/
│   ├── processed/
│   └── exports/
├── notebooks/
├── prompts/
├── logs/
├── docker-compose.yml
├── Dockerfile
├── .gitignore
├── .env.example
├── README.md
└── LICENSE
```

### Option 2: Microservices-Ready (For Future Scaling)

```
Finvista/
├── services/
│   ├── api_gateway/
│   ├── market_data/
│   ├── portfolio/
│   ├── warrants/
│   ├── analytics/
│   └── auth/
├── frontend/
├── shared/
│   ├── database/
│   ├── messaging/
│   ├── cache/
│   └── types/
├── infrastructure/
│   ├── monitoring/
│   ├── logging/
│   └── deployment/
├── scripts/
├── tools/
└── docs/
```

---

## Migration Strategy

### Phase 1: Backend Restructuring (Low Risk)
1. Create `apps/backend/` structure
2. Move `src/` → `apps/backend/app/`
3. Move `alembic/` → `apps/backend/alembic/`
4. Move `tests/` → `apps/backend/tests/`
5. Move backend scripts to `apps/backend/scripts/`
6. Update imports and paths

### Phase 2: Frontend Restructuring (Low Risk)
1. Create `apps/frontend/` structure
2. Move `frontend/` → `apps/frontend/`
3. Reorganize by feature domains
4. Update imports and paths

### Phase 3: Shared & Tools (Medium Risk)
1. Create `shared/` for common types/utils
2. Create `tools/` for development/deployment tools
3. Move root scripts to appropriate locations
4. Update CI/CD pipelines

### Phase 4: Domain Organization (High Risk)
1. Reorganize backend by domain (market, portfolio, warrants, analytics)
2. Implement proper layering (api → services → repositories)
3. Update all imports
4. Comprehensive testing

---

## Benefits of Proposed Structure

### 1. **Clear Separation of Concerns**
- Backend, frontend, and shared code clearly separated
- Domain logic organized by business area
- Infrastructure concerns isolated

### 2. **Scalability**
- Easy to extract microservices when needed
- Clear boundaries between domains
- Shared code properly managed

### 3. **Maintainability**
- Easier to locate code by domain
- Consistent structure across projects
- Better onboarding for new developers

### 4. **Testing**
- Clear test organization by layer
- Easy to run tests per domain
- Better test coverage tracking

### 5. **Deployment**
- Independent deployment of frontend/backend
- Clear configuration management
- Better Docker organization

---

## Recommendations

### Immediate Actions (This Week)
1. **Clean root directory**: Move all root scripts to `tools/` or `scripts/`
2. **Organize configs**: Move all configs to `config/` with environment subdirectories
3. **Create domain folders**: Start organizing backend modules by domain

### Short-term Actions (This Month)
1. **Implement Option 1**: Domain-driven monorepo structure
2. **Reorganize by feature**: Group related functionality
3. **Standardize naming**: Consistent naming conventions

### Long-term Actions (This Quarter)
1. **Consider microservices**: If scaling needs arise
2. **Implement shared packages**: For common utilities
3. **Optimize deployment**: Better Docker and CI/CD setup

---

## Comparison with Current Structure

| Aspect | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| Root clutter | ❌ High | ✅ Minimal | Clear separation |
| Domain organization | ❌ Mixed | ✅ Clear | Better maintainability |
| Scalability | ⚠️ Limited | ✅ High | Future-proof |
| Onboarding | ⚠️ Medium | ✅ Easy | Better DX |
| Testing | ⚠️ Basic | ✅ Structured | Better coverage |
| Deployment | ⚠️ Simple | ✅ Flexible | Multiple options |

---

**Last Updated:** 2026-07-28
**Next Review:** After Phase 1 completion
