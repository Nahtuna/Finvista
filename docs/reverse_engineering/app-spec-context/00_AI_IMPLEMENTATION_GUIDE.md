# AI Implementation Guide - FinLens Clone

## 🎯 Mục Đích

Tài liệu này hướng dẫn cách sử dụng bộ specification documents để AI implement FinLens Clone một cách có hệ thống, tránh bị "ảo tưởng" và đảm bảo chất lượng code.

---

## 📋 Cách Sử Dụng Bộ Specification

### Bước 1: Nạp Tài Liệu Vào AI

**Đối với Claude Projects/ChatGPT GPTs**:
1. Upload toàn bộ 5 files trong thư mục `app-spec-context/`:
   - `01_architecture.md`
   - `02_database_schema.md`
   - `03_api_endpoints.md`
   - `04_features_flow.md`
   - `05_coding_standards.md`

2. Yêu cầu AI đọc và hiểu toàn bộ tài liệu trước khi bắt đầu code.

**Đối với Cursor/Windsurf**:
1. Add toàn bộ files vào workspace
2. Sử dụng "Context" feature để include các files này
3. Set làm "reference documents" cho project

---

## 🤖 Prompt Strategy Cho AI

### Prompt 1: Initial Setup (KHÔNG CODE NGAY)

```
Tôi đã cung cấp toàn bộ tài liệu đặc tả (Specification) cho app FinLens Clone dựa trên việc reverse engineering app FinLens (https://finlensquant.vn).

Nhiệm vụ của bạn là giúp tôi code lại app này theo specification.

TUYÊN NHƯNG, CHƯA ĐƯỢC CODE NGAY.

Trước tiên, hãy:
1. Đọc toàn bộ 5 specification documents tôi đã nạp
2. Tóm tắt lại kiến trúc hệ thống theo các tầng (Frontend, Backend, Database, Infrastructure)
3. Đề xuất cho tôi một LỘ TRÌNH CODE TỪNG BƯỚC (Step-by-step Implementation Roadmap)
4. Chia nhỏ lộ trình theo thứ tự: Database → Base Backend → API → Frontend
5. Mỗi bước phải có:
   - Mục tiêu cụ thể
   - Files cần tạo/sửa
   - Dependencies cần thiết
   - Criteria để xác nhận hoàn thành (Definition of Done)

Khi tôi duyệt qua lộ trình đó, chúng ta mới bắt đầu code từng file một.
```

---

### Prompt 2: Database Implementation

```
Bắt đầu implement theo lộ trình đã duyệt.

GIAI ĐOẠN 1: DATABASE & BASE INFRASTRUCTURE

Theo file `02_database_schema.md`, hãy:

1. Tạo Alembic migration files cho tất cả tables đã định nghĩa
2. Implement database connection và session management trong `src/core/database.py`
3. Tạo SQLAlchemy ORM models tương ứng với schema
4. Viết unit tests cho database operations
5. Tạo seed data script để populate initial data

Yêu cầu:
- Follow coding standards trong `05_coding_standards.md`
- Sử dụng PostgreSQL dialect cho Supabase compatibility
- Include proper indexes và constraints
- Add docstrings cho tất cả models
- Write tests với pytest fixtures

Sau khi hoàn thành, báo cáo:
- Files đã tạo
- Test results
- Bất kỳ vấn đề hoặc deviation từ specification
```

---

### Prompt 3: Authentication System

```
GIAI ĐOẠN 2: AUTHENTICATION & USER MANAGEMENT

Theo file `03_api_endpoints.md` và `04_features_flow.md`, implement:

1. JWT authentication system (access + refresh tokens)
2. User registration endpoint với email verification
3. Login/logout endpoints
4. Password hashing với bcrypt
5. Rate limiting cho auth endpoints
6. User model và related database tables

Yêu cầu:
- Sử dụng httpOnly cookies cho token storage
- Implement token rotation cho refresh tokens
- Add comprehensive error handling
- Write integration tests cho auth flows
- Log auth events cho monitoring

Sau khi hoàn thành, test:
- Registration flow
- Login flow
- Token refresh flow
- Logout flow
- Rate limiting
```

---

### Prompt 4: Core API Endpoints

```
GIAI ĐOẠN 3: CORE API ENDPOINTS

Theo file `03_api_endpoints.md`, implement theo thứ tự:

1. CW Data endpoints (list, detail, history, dashboard)
2. Market data endpoints
3. Error handling middleware
4. Response formatting standard
5. Request validation với Pydantic

Yêu cầu:
- Sử dụng FastAPI dependency injection
- Implement proper error responses
- Add OpenAPI documentation
- Write integration tests cho mỗi endpoint
- Include rate limiting

Sau khi mỗi endpoint group, test với:
- curl/Postman
- Swagger UI (/docs)
- Integration tests
```

---

### Prompt 5: Business Logic Layer

```
GIAI ĐOẠN 4: BUSINESS LOGIC LAYER

Theo file `04_features_flow.md`, implement service layer cho:

1. CW Pricing Engine (Black-Scholes, Greeks calculation)
2. DeepFinLens Matrix calculation
3. Sector Analysis logic
4. Portfolio calculation logic
5. AI Committee integration (mock initially)

Yêu cầu:
- Tạo service classes trong `src/modules/`
- Implement proper error handling
- Add unit tests cho business logic
- Use type hints cho tất cả functions
- Include docstrings

Sau khi hoàn thành, test:
- Unit tests cho từng service
- Integration tests với database
- Performance tests cho heavy calculations
```

---

### Prompt 6: Frontend Setup

```
GIAI ĐOẠN 5: FRONTEND SETUP

Theo file `01_architecture.md`, setup:

1. Next.js 14 project với App Router
2. TypeScript configuration
3. TailwindCSS setup
4. Project structure theo `05_coding_standards.md`
5. ESLint và Prettier configuration
6. Environment variables setup

Yêu cầu:
- Sử dụng create-next-app với TypeScript
- Configure absolute imports
- Setup proper folder structure
- Add linting và formatting scripts
- Create base layout và error pages

Sau khi hoàn thành, verify:
- Build succeeds
- Linting passes
- TypeScript compilation succeeds
```

---

### Prompt 7: Frontend Components

```
GIAI ĐOẠN 6: FRONTEND COMPONENTS

Theo file `04_features_flow.md`, implement theo thứ tự:

1. Common components (Button, Input, Modal, etc.)
2. Dashboard components (ScatterPlot, ParetoChart)
3. DeepFinLens components (Matrix, CellDetail)
4. Sector Analysis components
5. Portfolio components
6. Authentication components (Login, Register)

Yêu cầu:
- Sử dụng functional components với hooks
- Implement proper TypeScript types
- Add unit tests với React Testing Library
- Follow accessibility standards
- Include error boundaries

Sau khi mỗi component group, test:
- Unit tests
- Visual regression (nếu có)
- Accessibility audit
```

---

### Prompt 8: State Management & API Integration

```
GIAI ĐOẠN 7: STATE MANAGEMENT & API INTEGRATION

Theo file `05_coding_standards.md`, implement:

1. Zustand stores (auth, marketData, portfolio)
2. API service layer với axios
3. React Query cho server state
4. WebSocket client cho real-time data
5. Error handling và retry logic

Yêu cầu:
- Implement proper TypeScript types
- Add optimistic updates
- Handle loading và error states
- Implement reconnection logic cho WebSocket
- Add unit tests cho stores

Sau khi hoàn thành, test:
- Store operations
- API calls với mocked responses
- WebSocket connection
- Error scenarios
```

---

### Prompt 9: Integration Testing

```
GIAI ĐOẠN 8: INTEGRATION TESTING

Implement end-to-end tests cho critical user flows:

1. User registration → Login → Dashboard access
2. CW Dashboard → View detail → Add to portfolio
3. Portfolio creation → Position entry → Exit
4. Subscription checkout → Payment verification
5. WebSocket connection → Real-time updates

Yêu cầu:
- Sử dụng Playwright cho E2E tests
- Test với real browser
- Include mobile viewport tests
- Test error scenarios
- Add visual regression (nếu có)

Sau khi hoàn thành, verify:
- All critical flows pass
- Tests are stable
- Coverage metrics
```

---

### Prompt 10: Deployment Preparation

```
GIAI ĐOẠN 9: DEPLOYMENT PREPARATION

Theo file `01_architecture.md`, prepare cho production:

1. Docker configuration cho backend
2. Environment variables template
3. Database migration scripts
4. CI/CD pipeline configuration (GitHub Actions)
5. Monitoring setup (Sentry integration)
6. Performance optimization

Yêu cầu:
- Create production-ready Dockerfile
- Configure proper environment handling
- Setup automated testing trong CI/CD
- Add health check endpoints
- Implement graceful shutdown

Sau khi hoàn thành, test:
- Docker build succeeds
- Environment variables work correctly
- CI/CD pipeline runs successfully
```

---

## 🎯 Best Practices Khi Làm Việc Với AI

### 1. Modular Development

**LUÔN BẮT AI LÀM THEO THỨ TỰ**:
1. Database + Auth → Test chạy được
2. Core API → Test với Swagger
3. Business Logic → Unit tests pass
4. Frontend Setup → Build succeeds
5. Components → Unit tests pass
6. Integration → E2E tests pass

**KHÔNG**:
- Implement tất cả cùng lúc
- Skip testing
- Move sang giai đoạn tiếp khi giai đoạn hiện tại chưa hoàn thành

---

### 2. Testing Strategy

**LUÔN YÊU CẦU AI VIẾT TESTS**:
- Unit tests cho business logic
- Integration tests cho API endpoints
- E2E tests cho critical user flows
- Performance tests cho heavy operations

**Test Coverage Targets**:
- Backend: >80% cho critical paths
- Frontend: >60% overall
- E2E: All critical flows covered

---

### 3. Code Review Checklist

**SAU KHI AI HOÀN THÀNH MỖI GIAI ĐOẠN**:

- [ ] Code follows coding standards trong `05_coding_standards.md`
- [ ] Type hints present và correct
- [ ] Docstrings included
- [ ] Error handling comprehensive
- [ ] Security best practices followed
- [ ] Tests included và passing
- [ ] No hardcoded credentials
- [ ] Performance considered
- [ ] Documentation adequate

---

### 4. Handling AI Hallucinations

**KHI AI ĐƯA RA THÔNG TIN KHÔNG CÓ TRONG SPECIFICATION**:

1. Ask AI to cite source trong specification documents
2. Verify thông tin với specification
3. Nếu không có trong spec, ask AI to note as "assumption"
4. Document assumptions trong separate file
5. Review assumptions với stakeholder

---

### 5. Iterative Refinement

**KHI AI CODE KHÔNG ĐÚNG YÊU CẦU**:

1. Cite specific section trong specification document
2. Provide example của expected behavior
3. Ask AI to explain deviation
4. Request fix với specific reference
5. Verify fix meets requirement

---

## 🚨 Common Issues & Solutions

### Issue 1: AI Ignores Specification

**Symptom**: AI implement features không có trong spec hoặc khác với spec

**Solution**:
```
Theo file [X], section [Y], requirement là [Z].
Code hiện tại đang implement [A], khác với requirement.
Vui lòng sửa để match specification.
```

---

### Issue 2: AI Skips Testing

**Symptom**: AI không viết tests hoặc tests không adequate

**Solution**:
```
Theo coding standards trong file 05_coding_standards.md,
tất cả functions phải có unit tests.
Vui lòng viết tests cho [function/class] với pytest.
```

---

### Issue 3: AI Uses Wrong Tech Stack

**Symptom**: AI sử dụng library/framework không có trong spec

**Solution**:
```
Theo file 01_architecture.md, tech stack yêu cầu là [X].
Code hiện tại đang sử dụng [Y], không đúng spec.
Vui lòng refactor để sử dụng [X].
```

---

### Issue 4: AI Code Not Production-Ready

**Symptom**: Code thiếu error handling, logging, security

**Solution**:
```
Theo coding standards trong file 05_coding_standards.md,
code phải có:
- Proper error handling
- Logging với appropriate levels
- Security best practices
- Type hints
- Docstrings

Vui lòng review và fix [file/function].
```

---

## 📊 Progress Tracking

### Milestone Checklist

**Phase 1: Foundation** (Week 1-2)
- [ ] Database schema implemented
- [ ] Authentication system working
- [ ] Base API endpoints functional
- [ ] Tests passing

**Phase 2: Core Features** (Week 3-4)
- [ ] CW pricing engine complete
- [ ] Dashboard components working
- [ ] Real-time data via WebSocket
- [ ] Integration tests passing

**Phase 3: Advanced Features** (Week 5-6)
- [ ] DeepFinLens Matrix working
- [ ] Sector Analysis complete
- [ ] Portfolio management functional
- [ ] E2E tests passing

**Phase 4: Production Ready** (Week 7-8)
- [ ] Performance optimization
- [ ] Security audit
- [ ] Deployment configuration
- [ ] Monitoring setup

---

## 🔄 Feedback Loop

### Weekly Review Process

1. **Review Progress**: Check milestone completion
2. **Test Coverage**: Verify test metrics meet targets
3. **Code Quality**: Run linting và type checking
4. **Performance**: Profile critical paths
5. **Security**: Review security practices
6. **Documentation**: Ensure docs updated

### Adjustment Process

1. **Identify Issues**: Log deviations from spec
2. **Root Cause Analysis**: Understand why deviation occurred
3. **Corrective Action**: Fix issue hoặc update spec
4. **Prevention**: Update process để prevent recurrence
5. **Documentation**: Document lessons learned

---

## 📚 Additional Resources

### Specification Documents Reference

- **Architecture**: `01_architecture.md` - Tech stack, system design
- **Database**: `02_database_schema.md` - Tables, relationships, indexes
- **API**: `03_api_endpoints.md` - Endpoints, request/response formats
- **Features**: `04_features_flow.md` - User stories, acceptance criteria
- **Standards**: `05_coding_standards.md` - Coding conventions, best practices

### External References

- **FastAPI**: https://fastapi.tiangolo.com/
- **Next.js**: https://nextjs.org/docs
- **PostgreSQL**: https://www.postgresql.org/docs/
- **TailwindCSS**: https://tailwindcss.com/docs
- **Zustand**: https://github.com/pmndrs/zustand

---

## 🎯 Success Criteria

### Technical Success
- [ ] All specification requirements implemented
- [ ] Test coverage meets targets
- [ ] Code quality standards met
- [ ] Performance benchmarks achieved
- [ ] Security requirements satisfied

### Functional Success
- [ ] All user flows working as specified
- [ ] Real-time data updates functional
- [ ] Authentication/authorization working
- [ ] Error handling comprehensive
- [ ] Edge cases handled properly

### Deployment Success
- [ ] Application deployable to production
- [ ] CI/CD pipeline functional
- [ ] Monitoring configured
- [ ] Backup strategy in place
- [ ] Disaster recovery documented

---

## 📝 Notes & Assumptions

### Documented Assumptions

Khi AI làm assumptions không có trong spec, document ở đây:

```
[Date]: [Assumption]
- Reason: Why assumption was made
- Impact: How this affects implementation
- Decision: Keep or revisit
```

### Lessons Learned

Document lessons learned during implementation:

```
[Date]: [Lesson]
- Context: What happened
- Lesson: What was learned
- Action: How to apply going forward
```

---

## 🚀 Next Steps

Sau khi hoàn thành implementation:

1. **User Acceptance Testing**: Test với real users
2. **Performance Tuning**: Optimize based on real usage
3. **Feature Expansion**: Add features based on feedback
4. **Documentation Updates**: Update docs based on actual implementation
5. **Maintenance Planning**: Plan for ongoing maintenance

---

## 📞 Support

Khi gặp issues không thể resolve với AI:

1. Review specification documents again
2. Check coding standards
3. Look for similar patterns trong existing code
4. Consult external documentation
5. Ask for human review nếu needed

---

**Remember**: Specification documents là "source of truth". Khi có conflict giữa AI output và specification, specification takes precedence.
