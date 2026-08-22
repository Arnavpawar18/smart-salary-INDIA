# SMART SALARY INDIA — RELATIONAL DATABASE SCHEMA

---

## 1. Entity-Relationship Overview

```
 [ users ] ──────────< [ user_profiles ]
    │
    ├────────────────< [ calculations ] ──────────< [ calculation_traces ]
    │
    └────────────────< [ organization_members ] >────────── [ organizations ]
                                                                  │
                                      ┌───────────────────────────┴───────────────────────────┐
                                      ▼                                                       ▼
                                [ employees ]                                       [ salary_structures ]
                                      │                                                       │
                                      └─────────────────────┬─────────────────────────────────┘
                                                            ▼
                                                     [ payroll_runs ] ──────────< [ payslips ]
```

---

## 2. Core Tables Specification

### 2.1 Users & Authentication (`users`, `user_profiles`)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(50) DEFAULT 'INDIVIDUAL',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    employment_type VARCHAR(50), -- private, central_govt, state_govt, psu, freelancer, business
    industry VARCHAR(100),
    state_code VARCHAR(10),
    city VARCHAR(100),
    company_name VARCHAR(255),
    designation VARCHAR(150),
    annual_ctc NUMERIC(15, 2),
    preferred_regime VARCHAR(20) DEFAULT 'NEW',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.2 Versioned Regulatory Rules (`tax_rules`, `pf_rules`, `pt_rules`, `sources`)
```sql
CREATE TABLE government_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    authority VARCHAR(150) NOT NULL, -- CBDT, EPFO, ESIC, Karnataka Dept of Commercial Taxes
    jurisdiction VARCHAR(50) NOT NULL, -- CENTRAL / STATE
    state_code VARCHAR(10),
    official_url VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tax_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code VARCHAR(100) NOT NULL,
    financial_year VARCHAR(20) NOT NULL, -- e.g. 2025-26
    regime VARCHAR(20) NOT NULL, -- NEW / OLD
    standard_deduction NUMERIC(12, 2) NOT NULL,
    slabs JSONB NOT NULL,
    rebate_config JSONB NOT NULL,
    cess_rate NUMERIC(5, 4) DEFAULT 0.04,
    effective_from DATE NOT NULL,
    effective_until DATE,
    source_id UUID REFERENCES government_sources(id),
    version VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE professional_tax_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state_code VARCHAR(10) NOT NULL,
    state_name VARCHAR(100) NOT NULL,
    financial_year VARCHAR(20) NOT NULL,
    slabs JSONB NOT NULL, -- Array of [{min, max, monthly_tax, feb_tax, gender_condition}]
    effective_from DATE NOT NULL,
    effective_until DATE,
    source_id UUID REFERENCES government_sources(id),
    version VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.3 Calculations & Audit Trails (`calculations`, `calculation_traces`)
```sql
CREATE TABLE calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    financial_year VARCHAR(20) NOT NULL,
    regime VARCHAR(20) NOT NULL,
    annual_ctc NUMERIC(15, 2) NOT NULL,
    gross_salary NUMERIC(15, 2) NOT NULL,
    total_tax NUMERIC(15, 2) NOT NULL,
    employee_pf NUMERIC(15, 2) NOT NULL,
    employer_pf NUMERIC(15, 2) NOT NULL,
    esi NUMERIC(15, 2) NOT NULL,
    professional_tax NUMERIC(15, 2) NOT NULL,
    net_take_home_monthly NUMERIC(15, 2) NOT NULL,
    net_take_home_annual NUMERIC(15, 2) NOT NULL,
    input_payload JSONB NOT NULL,
    output_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE calculation_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calculation_id UUID REFERENCES calculations(id) ON DELETE CASCADE,
    component_name VARCHAR(100) NOT NULL, -- INCOME_TAX, EPF, ESI, PROFESSIONAL_TAX
    rule_version_id VARCHAR(100) NOT NULL,
    formula_applied TEXT NOT NULL,
    input_amount NUMERIC(15, 2) NOT NULL,
    calculated_amount NUMERIC(15, 2) NOT NULL,
    source_reference TEXT NOT NULL,
    explanation_summary TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2.4 Organization & Payroll (`organizations`, `employees`, `payroll_runs`, `payslips`)
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    legal_type VARCHAR(100),
    state_code VARCHAR(10),
    pan_tan_masked VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    employee_code VARCHAR(50) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255),
    designation VARCHAR(150),
    department VARCHAR(100),
    joining_date DATE,
    state_code VARCHAR(10) NOT NULL,
    annual_ctc NUMERIC(15, 2) NOT NULL,
    status VARCHAR(30) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payroll_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    month INT NOT NULL, -- 1-12
    year INT NOT NULL,
    total_gross NUMERIC(15, 2) NOT NULL,
    total_statutory_deductions NUMERIC(15, 2) NOT NULL,
    total_net_payout NUMERIC(15, 2) NOT NULL,
    status VARCHAR(30) DEFAULT 'DRAFT', -- DRAFT, APPROVED, DISBURSED
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payslips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_run_id UUID REFERENCES payroll_runs(id) ON DELETE CASCADE,
    employee_id UUID REFERENCES employees(id) ON DELETE CASCADE,
    month INT NOT NULL,
    year INT NOT NULL,
    basic_salary NUMERIC(12, 2) NOT NULL,
    hra NUMERIC(12, 2) NOT NULL,
    allowances NUMERIC(12, 2) NOT NULL,
    gross_pay NUMERIC(12, 2) NOT NULL,
    employee_pf NUMERIC(12, 2) NOT NULL,
    employee_esi NUMERIC(12, 2) NOT NULL,
    professional_tax NUMERIC(12, 2) NOT NULL,
    tds NUMERIC(12, 2) NOT NULL,
    net_pay NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
