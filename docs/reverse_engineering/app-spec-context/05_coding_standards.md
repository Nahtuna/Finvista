# 05. Coding Standards - FinLens Clone

## 📋 Overview

Coding standards đảm bảo consistency, maintainability và quality của codebase. Tất cả developers (và AI) phải tuân theo standards này.

---

## 🐍 Python Standards (Backend)

### File Structure & Naming

**File Naming**:
- Use `snake_case` cho file names: `user_service.py`, `cw_pricing_engine.py`
- Module names: lowercase với underscores
- Package names: lowercase, short, no underscores

**Class Naming**:
- Use `PascalCase` cho classes: `UserService`, `CWPricingEngine`
- Use descriptive names, avoid abbreviations

**Function/Variable Naming**:
- Use `snake_case` cho functions và variables: `get_user_data()`, `user_id`
- Use descriptive names, avoid single letters except loop counters
- Constants: `UPPER_SNAKE_CASE`: `MAX_RETRY_ATTEMPTS`

**Example**:
```python
# ✅ Good
class UserService:
    def get_user_by_id(self, user_id: str) -> User:
        pass

# ❌ Bad
class userService:
    def getUserByID(self, uid):
        pass
```

---

### Type Hints

**Mandatory Type Hints**:
- All functions phải có type hints cho parameters và return values
- Use `typing` module cho complex types
- Use `Optional` cho nullable types

**Example**:
```python
from typing import List, Dict, Optional, Union
from datetime import datetime

def get_cw_data(
    symbol: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Union[str, float, int]]]:
    """Fetch CW data for given symbol and date range."""
    pass
```

---

### Docstrings

**Google Style Docstrings**:
- All functions, classes, modules phải có docstrings
- Use Google style format
- Include: description, args, returns, raises, examples

**Example**:
```python
def calculate_greeks(
    spot_price: float,
    strike_price: float,
    time_to_maturity: float,
    volatility: float,
    risk_free_rate: float = 0.05
) -> Dict[str, float]:
    """Calculate option Greeks using Black-Scholes model.
    
    Args:
        spot_price: Current price of the underlying asset
        strike_price: Strike price of the option
        time_to_maturity: Time to maturity in years
        volatility: Implied volatility of the underlying
        risk_free_rate: Risk-free interest rate (default: 0.05)
    
    Returns:
        Dictionary containing Greeks:
            - delta: Sensitivity to underlying price
            - gamma: Sensitivity of delta to underlying price
            - theta: Sensitivity to time decay
            - vega: Sensitivity to volatility
            - rho: Sensitivity to interest rate
    
    Raises:
        ValueError: If inputs are invalid (negative values, etc.)
    
    Example:
        >>> greeks = calculate_greeks(100, 95, 0.25, 0.3)
        >>> print(greeks['delta'])
        0.65
    """
    pass
```

---

### Error Handling

**Specific Exception Handling**:
- Catch specific exceptions, not bare `except:`
- Use custom exceptions cho business logic errors
- Always include meaningful error messages
- Log errors with context

**Example**:
```python
# ✅ Good
try:
    user = get_user(user_id)
except UserNotFoundError as e:
    logger.error(f"User not found: {user_id}", exc_info=True)
    raise HTTPException(status_code=404, detail=str(e))
except DatabaseError as e:
    logger.error(f"Database error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")

# ❌ Bad
try:
    user = get_user(user_id)
except:
    raise HTTPException(status_code=500, detail="Error")
```

**Custom Exceptions**:
```python
class FinLensError(Exception):
    """Base exception for FinLens application."""
    pass

class CWNotFoundError(FinLensError):
    """Raised when CW symbol is not found."""
    pass

class InsufficientDataError(FinLensError):
    """Raised when insufficient data for calculation."""
    pass
```

---

### Logging

**Structured Logging**:
- Use `logging` module, not `print()`
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include context in log messages
- Use structured logging cho production

**Example**:
```python
import logging

logger = logging.getLogger(__name__)

def process_cw_data(symbol: str):
    logger.info(f"Processing CW data for {symbol}")
    
    try:
        data = fetch_cw_data(symbol)
        logger.debug(f"Fetched {len(data)} records for {symbol}")
        
        result = calculate_metrics(data)
        logger.info(f"Successfully processed {symbol}", extra={
            'symbol': symbol,
            'record_count': len(data),
            'processing_time_ms': 123
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to process {symbol}: {e}", exc_info=True)
        raise
```

---

### Database Operations

**SQLAlchemy Best Practices**:
- Use ORM for CRUD operations
- Use raw SQL only cho complex queries
- Always use parameterized queries (ORM handles this)
- Use transactions cho multi-step operations
- Handle connection errors gracefully

**Example**:
```python
# ✅ Good - Using ORM
def get_active_cws(db: Session) -> List[CW]:
    return db.query(CW).filter(CW.is_active == True).all()

# ✅ Good - Using transaction
def update_portfolio(db: Session, portfolio_id: str, updates: Dict):
    try:
        db.begin()
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        
        for key, value in updates.items():
            setattr(portfolio, key, value)
            
        db.commit()
        return portfolio
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update portfolio: {e}")
        raise

# ❌ Bad - Raw SQL with user input
def get_user_by_name(db: Session, name: str):
    query = f"SELECT * FROM users WHERE name = '{name}'"  # SQL injection risk!
    return db.execute(query)
```

---

### API Design (FastAPI)

**RESTful Conventions**:
- Use appropriate HTTP methods: GET, POST, PUT, DELETE
- Use plural nouns cho resource names: `/api/v1/cw`, `/api/v1/portfolios`
- Use kebab-case cho URL paths: `/api/v1/cw-market-data`
- Return consistent response format

**Response Format**:
```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None

# Usage
@router.get("/cw/{symbol}")
async def get_cw(symbol: str) -> ApiResponse[CWDetail]:
    try:
        cw = cw_service.get_cw_by_symbol(symbol)
        return ApiResponse(success=True, data=cw)
    except CWNotFoundError:
        return ApiResponse(success=False, error="CW_NOT_FOUND", message="CW not found")
```

**Dependency Injection**:
```python
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/cw/{symbol}")
async def get_cw(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return cw_service.get_cw_by_symbol(db, symbol, current_user.id)
```

---

### Testing Standards

**Pytest Structure**:
```python
# tests/test_cw_service.py
import pytest
from unittest.mock import Mock, patch

class TestCWService:
    
    @pytest.fixture
    def cw_service(self):
        return CWService()
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    def test_get_cw_by_symbol_success(self, cw_service, mock_db):
        # Arrange
        symbol = "CACB2511"
        expected_cw = CW(symbol=symbol, underlying="ACB")
        mock_db.query.return_value.filter.return_value.first.return_value = expected_cw
        
        # Act
        result = cw_service.get_cw_by_symbol(mock_db, symbol)
        
        # Assert
        assert result.symbol == symbol
        assert result.underlying == "ACB"
    
    def test_get_cw_by_symbol_not_found(self, cw_service, mock_db):
        # Arrange
        symbol = "INVALID"
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(CWNotFoundError):
            cw_service.get_cw_by_symbol(mock_db, symbol)
```

**Test Coverage**:
- Unit tests cho business logic (>80% coverage)
- Integration tests cho API endpoints
- End-to-end tests cho critical user flows
- Performance tests cho heavy computations

---

## ⚛️ React/TypeScript Standards (Frontend)

### File Structure

**Component Organization**:
```
src/
├── components/
│   ├── common/
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx
│   │   │   └── index.ts
│   │   └── Input/
│   ├── dashboard/
│   │   ├── ScatterPlot/
│   │   │   ├── ScatterPlot.tsx
│   │   │   ├── ScatterPlot.test.tsx
│   │   │   └── index.ts
│   │   └── ParetoChart/
├── hooks/
│   ├── useAuth.ts
│   ├── useCWData.ts
│   └── useWebSocket.ts
├── services/
│   ├── api.ts
│   ├── cwService.ts
│   └── authService.ts
├── stores/
│   ├── authStore.ts
│   ├── marketDataStore.ts
│   └── portfolioStore.ts
├── types/
│   ├── cw.types.ts
│   ├── user.types.ts
│   └── api.types.ts
└── utils/
    ├── formatters.ts
    ├── validators.ts
    └── constants.ts
```

---

### Component Standards

**Functional Components**:
- Use functional components với hooks
- Avoid class components (unless necessary)
- Use TypeScript interfaces cho props

**Example**:
```typescript
// ✅ Good
interface ScatterPlotProps {
  data: CWDataPoint[];
  onPointClick: (symbol: string) => void;
  className?: string;
}

export const ScatterPlot: React.FC<ScatterPlotProps> = ({
  data,
  onPointClick,
  className = ""
}) => {
  // Component logic
  return <div className={className}>{/* JSX */}</div>;
};

// ❌ Bad
export class ScatterPlot extends React.Component {
  render() {
    return <div>{/* JSX */}</div>;
  }
}
```

---

### TypeScript Standards

**Type Definitions**:
```typescript
// types/cw.types.ts
export interface CWDataPoint {
  symbol: string;
  underlying: string;
  x: number;  // delta
  y: number;  // premium
  size: number;  // volume
  color: string;
  opportunityScore: number;
  decisionSignal: 'buy' | 'sell' | 'hold' | 'neutral';
}

export interface CWDetail extends CWDataPoint {
  strikePrice: number;
  maturityDate: string;
  daysToMaturity: number;
  issuer: string;
  greeks: {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
  };
}

export type DecisionSignal = CWDetail['decisionSignal'];
```

**Strict Mode**:
- Enable `strict: true` trong `tsconfig.json`
- Avoid `any` type, use `unknown` nếu cần
- Use proper null checks: `optional chaining` (`?.`) và `nullish coalescing` (`??`)

---

### Hooks Standards

**Custom Hooks**:
```typescript
// hooks/useCWData.ts
import { useState, useEffect } from 'react';
import { cwService } from '@/services/cwService';

interface UseCWDataResult {
  data: CWDataPoint[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useCWData = (symbol?: string): UseCWDataResult => {
  const [data, setData] = useState<CWDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await cwService.getCWData(symbol);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [symbol]);

  return { data, loading, error, refetch: fetchData };
};
```

---

### State Management (Zustand)

**Store Structure**:
```typescript
// stores/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      login: async (email, password) => {
        const response = await authService.login(email, password);
        set({
          user: response.user,
          token: response.access_token,
          isAuthenticated: true
        });
      },
      
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false
        });
      }
    }),
    {
      name: 'auth-storage'
    }
  )
);
```

---

### API Service Layer

**Service Pattern**:
```typescript
// services/cwService.ts
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000
});

// Request interceptor
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

export const cwService = {
  async getCWData(symbol?: string): Promise<CWDataPoint[]> {
    const params = symbol ? { symbol } : {};
    const response = await api.get('/cw/dashboard', { params });
    return response.data.scatter_data;
  },
  
  async getCWDetail(symbol: string): Promise<CWDetail> {
    const response = await api.get(`/cw/${symbol}`);
    return response.data;
  }
};
```

---

### Styling Standards (TailwindCSS)

**Component Styling**:
```typescript
// ✅ Good - Using Tailwind classes
export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  children,
  ...props
}) => {
  const baseClasses = 'rounded-lg font-medium transition-colors';
  
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    danger: 'bg-red-600 text-white hover:bg-red-700'
  };
  
  const sizeClasses = {
    small: 'px-3 py-1.5 text-sm',
    medium: 'px-4 py-2 text-base',
    large: 'px-6 py-3 text-lg'
  };
  
  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]}`}
      {...props}
    >
      {children}
    </button>
  );
};

// ❌ Bad - Inline styles
export const Button: React.FC<ButtonProps> = ({ children }) => {
  return (
    <button style={{
      backgroundColor: 'blue',
      color: 'white',
      padding: '8px 16px',
      borderRadius: '8px'
    }}>
      {children}
    </button>
  );
};
```

---

### Error Handling

**Error Boundaries**:
```typescript
// components/common/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
        </div>
      );
    }

    return this.props.children;
  }
}
```

---

## 🗄️ Database Standards

### Migration Standards

**Alembic Migrations**:
```python
# alembic/versions/001_create_users_table.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('subscription_tier', sa.String(20), nullable=False, server_default='demo'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("subscription_tier IN ('demo', 'client', 'client_pro')", name='check_subscription_tier')
    )
    
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_subscription_tier', 'users', ['subscription_tier'])

def downgrade():
    op.drop_index('idx_users_subscription_tier', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
```

---

### Query Optimization

**Indexing Strategy**:
- Create indexes cho foreign keys
- Create indexes cho frequently filtered columns
- Use composite indexes cho common query patterns
- Monitor query performance với EXPLAIN ANALYZE

**Example**:
```sql
-- Good composite index for time-series queries
CREATE INDEX idx_cw_market_symbol_time 
ON cw_market_data(symbol, timestamp DESC);

-- Partial index for active records only
CREATE INDEX idx_cw_active 
ON cw_info(symbol) 
WHERE is_active = true;
```

---

## 🔒 Security Standards

### Authentication

**JWT Best Practices**:
- Use httpOnly cookies cho token storage (XSS protection)
- Use short-lived access tokens (15 minutes)
- Use refresh tokens với rotation
- Validate token signature on every request
- Implement token revocation list

**Example**:
```python
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

---

### Input Validation

**Pydantic Models**:
```python
from pydantic import BaseModel, validator, Field

class CWCreateRequest(BaseModel):
    symbol: str = Field(..., min_length=5, max_length=20, regex=r'^[A-Z]{4}\d{4}$')
    underlying: str = Field(..., min_length=2, max_length=10)
    strike_price: float = Field(..., gt=0)
    maturity_date: datetime = Field(..., gt=datetime.now())
    
    @validator('symbol')
    def validate_symbol_format(cls, v):
        if not re.match(r'^[A-Z]{4}\d{4}$', v):
            raise ValueError('Symbol must be in format XXXX1234')
        return v.upper()
```

---

### SQL Injection Prevention

**Parameterized Queries**:
```python
# ✅ Good - Using ORM (automatic parameterization)
users = db.query(User).filter(User.email == email).all()

# ✅ Good - Using text() with bind parameters
from sqlalchemy import text
result = db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})

# ❌ Bad - String formatting (SQL injection risk)
query = f"SELECT * FROM users WHERE email = '{email}'"
result = db.execute(query)
```

---

## 🚀 Performance Standards

### Caching Strategy

**Redis Caching**:
```python
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(ttl: int = 300):
    """Decorator to cache function results in Redis."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator

@cache_result(ttl=60)
def get_cw_dashboard_data(strategy: str = 'balanced'):
    # Expensive database query
    return cw_service.get_dashboard_data(strategy)
```

---

### Async Operations

**Async/Await Pattern**:
```python
import asyncio

async def fetch_multiple_cw_data(symbols: List[str]) -> List[CWData]:
    """Fetch data for multiple CWs concurrently."""
    tasks = [fetch_single_cw_data(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions
    return [r for r in results if not isinstance(r, Exception)]
```

---

## 📝 Git Standards

### Commit Messages

**Conventional Commits**:
```
feat: add CW scatter plot visualization
fix: resolve WebSocket reconnection issue
docs: update API documentation
refactor: simplify portfolio calculation logic
test: add unit tests for CW pricing engine
chore: update dependencies
```

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

---

### Branch Strategy

**Git Flow**:
```
main (production)
├── develop (staging)
├── feature/dashboard-scatter-plot
├── feature/deepfinlens-matrix
├── fix/websocket-reconnection
└── hotfix/critical-security-patch
```

---

## 🧪 Testing Standards

### Test Organization

**Pytest Structure**:
```
tests/
├── unit/
│   ├── test_cw_service.py
│   ├── test_auth_service.py
│   └── test_portfolio_service.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_database_operations.py
├── e2e/
│   ├── test_user_flow.py
│   └── test_trading_flow.py
└── conftest.py
```

---

### Test Data Management

**Fixtures**:
```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_cw():
    return CW(
        symbol="CACB2511",
        underlying="ACB",
        strike_price=25.5,
        maturity_date="2025-11-20"
    )
```

---

## 📊 Code Review Standards

### Review Checklist

**Functionality**:
- [ ] Code implements the requirements
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] Tests are included and passing

**Code Quality**:
- [ ] Code follows coding standards
- [ ] Names are descriptive and consistent
- [ ] Functions are small and focused
- [ ] No code duplication
- [ ] Comments are necessary and helpful

**Performance**:
- [ ] No obvious performance issues
- [ ] Database queries are optimized
- [ ] Caching is used where appropriate
- [ ] No memory leaks

**Security**:
- [ ] No hardcoded secrets
- [ ] Input validation is present
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] Authentication/authorization is correct

---

## 🔄 CI/CD Standards

### Pipeline Stages

**GitHub Actions Workflow**:
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run ruff
        run: ruff check src/
      - name: Run black
        run: black --check src/

  build:
    needs: [test, lint]
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: docker build -t finlens-clone .
```

---

## 📚 Documentation Standards

### Code Documentation

**Inline Comments**:
- Use comments để explain WHY, not WHAT
- Comment complex algorithms
- Document workarounds và temporary solutions
- Keep comments up-to-date with code changes

**Example**:
```python
# ✅ Good - Explains WHY
# Using exponential backoff to avoid overwhelming the API during rate limit errors
retry_delay = min(initial_delay * (2 ** attempt), max_delay)

# ❌ Bad - Explains WHAT (obvious from code)
# Increment retry_delay
retry_delay = retry_delay * 2
```

---

## 🎯 AI-Specific Guidelines

### When AI Generates Code

**Review Checklist**:
- [ ] Code follows all coding standards
- [ ] Type hints are present and correct
- [ ] Error handling is comprehensive
- [ ] Security best practices are followed
- [ ] Performance is considered
- [ ] Tests are included
- [ ] Documentation is adequate
- [ ] No hardcoded credentials or sensitive data

**AI Prompt Guidelines**:
- Always include context about existing codebase
- Specify coding standards to follow
- Request type hints and docstrings
- Ask for error handling
- Request tests for new functions
- Specify performance requirements

---

## 📏 Code Metrics

**Quality Targets**:
- **Test Coverage**: >80% for critical paths, >60% overall
- **Cyclomatic Complexity**: <10 per function
- **Function Length**: <50 lines
- **File Length**: <500 lines
- **Code Duplication**: <5% (detected by tools)
- **Linting**: Zero warnings
- **Type Coverage**: >90% for TypeScript

---

## 🚫 Anti-Patterns

### Common Mistakes to Avoid

**Python**:
```python
# ❌ Don't use bare except
try:
    risky_operation()
except:
    pass

# ❌ Don't ignore type hints
def process_data(data):  # Missing type hints
    return data

# ❌ Don't use mutable default arguments
def append_to_list(item, items=[]):  # Dangerous!
    items.append(item)
    return items
```

**TypeScript/React**:
```typescript
// ❌ Don't use any
const processData = (data: any) => {
  return data.map((item: any) => item.value);
};

// ❌ Don't ignore useEffect dependencies
useEffect(() => {
  fetchData();
}, []);  // Missing dependencies

// ❌ Don't use index as key in lists
{items.map((item, index) => (
  <div key={index}>{item.name}</div>  // Bad for reordering
))}
```

---

## 📖 Resources

**Documentation**:
- [PEP 8 Style Guide](https://pep8.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)

**Tools**:
- **Linting**: ruff (Python), ESLint (TypeScript)
- **Formatting**: black (Python), Prettier (TypeScript)
- **Type Checking**: mypy (Python), tsc (TypeScript)
- **Testing**: pytest (Python), Jest (TypeScript)
- **Coverage**: pytest-cov (Python), istanbul (TypeScript)
