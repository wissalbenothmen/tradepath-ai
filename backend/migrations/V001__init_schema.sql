-- TradePath AI - Initial Schema
-- PostgreSQL migration

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enums
CREATE TYPE user_role AS ENUM (
    'customs_broker', 'trade_compliance', 'import_export_manager',
    'freight_forwarder', 'legal_counsel', 'executive', 'admin'
);

CREATE TYPE shipment_status AS ENUM (
    'draft', 'screening', 'classification', 'declaration_ready',
    'filed', 'cleared', 'hold', 'blocked'
);

CREATE TYPE transport_mode AS ENUM ('sea', 'air', 'road', 'rail', 'multimodal');

CREATE TYPE classification_status AS ENUM (
    'pending', 'classified', 'confirmed', 'disputed', 'escalated'
);

CREATE TYPE declaration_type AS ENUM ('cbp_entry_01', 'eu_sad', 'uk_c88', 'aes_filing');
CREATE TYPE declaration_status AS ENUM ('draft', 'review', 'submitted', 'accepted', 'rejected');

CREATE TYPE screening_result AS ENUM ('clear', 'potential_match', 'positive_match');

CREATE TYPE coo_format AS ENUM ('form_a_gsp', 'eur1', 'usmca', 'bilateral', 'generic');
CREATE TYPE origin_criterion AS ENUM (
    'wholly_obtained', 'substantial_transformation', 'tariff_shift', 'regional_value_content'
);

CREATE TYPE document_type AS ENUM (
    'commercial_invoice', 'packing_list', 'bill_of_lading', 'airway_bill',
    'certificate_of_origin', 'phytosanitary', 'import_license', 'export_license', 'other'
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'customs_broker',
    company_id UUID NOT NULL,
    is_active VARCHAR(5) NOT NULL DEFAULT 'true',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_company ON users(company_id);

-- Shipments
CREATE TABLE shipments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_number VARCHAR(50) UNIQUE NOT NULL,
    company_id UUID NOT NULL,
    created_by UUID NOT NULL,
    status shipment_status NOT NULL DEFAULT 'draft',
    transport_mode transport_mode,
    origin_country VARCHAR(3) NOT NULL,
    destination_country VARCHAR(3) NOT NULL,
    incoterms VARCHAR(10),
    exporter_name VARCHAR(255),
    exporter_country VARCHAR(3),
    importer_name VARCHAR(255),
    consignee_name VARCHAR(255),
    notify_party VARCHAR(255),
    manufacturer_name VARCHAR(255),
    freight_forwarder VARCHAR(255),
    total_value_usd FLOAT,
    total_weight_kg FLOAT,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    shipment_date DATE,
    denied_party_status VARCHAR(20),
    restriction_status VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_shipments_company ON shipments(company_id);
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_shipments_reference ON shipments(reference_number);

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL,
    sku VARCHAR(100),
    description TEXT NOT NULL,
    materials TEXT,
    intended_use TEXT,
    hs_code VARCHAR(15),
    hs_code_us_hts VARCHAR(15),
    hs_code_eu_taric VARCHAR(15),
    hs_code_uk_gt VARCHAR(15),
    classification_confidence FLOAT,
    gri_reasoning TEXT,
    cbp_binding_ruling VARCHAR(50),
    is_itar VARCHAR(5) NOT NULL DEFAULT 'false',
    is_ear VARCHAR(5) NOT NULL DEFAULT 'false',
    country_of_origin VARCHAR(3),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_products_company ON products(company_id);
CREATE INDEX idx_products_sku ON products(sku);

-- Shipment Line Items
CREATE TABLE shipment_line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    line_number INTEGER NOT NULL DEFAULT 1,
    description TEXT NOT NULL,
    quantity FLOAT NOT NULL DEFAULT 1.0,
    unit_of_measure VARCHAR(20),
    unit_price_usd FLOAT,
    total_value_usd FLOAT,
    weight_kg FLOAT,
    country_of_origin VARCHAR(3),
    hs_code VARCHAR(15),
    hs_code_confirmed VARCHAR(5) NOT NULL DEFAULT 'false',
    is_itar_ear VARCHAR(5) NOT NULL DEFAULT 'false',
    license_required VARCHAR(5) NOT NULL DEFAULT 'false',
    license_number VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_line_items_shipment ON shipment_line_items(shipment_id);

-- HS Classifications
CREATE TABLE hs_classifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    line_item_id UUID REFERENCES shipment_line_items(id),
    classified_by UUID NOT NULL,
    status classification_status NOT NULL DEFAULT 'pending',
    hs_code_6digit VARCHAR(10) NOT NULL,
    hs_code_us_hts VARCHAR(15),
    hs_code_eu_taric VARCHAR(15),
    hs_code_uk_gt VARCHAR(15),
    confidence FLOAT NOT NULL DEFAULT 0.0,
    gri_rules_applied JSONB,
    top_candidates JSONB,
    gpt_reasoning TEXT,
    cbp_binding_ruling_ref VARCHAR(50),
    duty_rate_us FLOAT,
    duty_rate_eu FLOAT,
    anti_dumping_duty FLOAT,
    is_itar_ear_flagged VARCHAR(5) NOT NULL DEFAULT 'false',
    confirmed_by UUID,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_hs_class_product ON hs_classifications(product_id);
CREATE INDEX idx_hs_class_line_item ON hs_classifications(line_item_id);

-- Customs Declarations
CREATE TABLE customs_declarations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    created_by UUID NOT NULL,
    declaration_type declaration_type NOT NULL,
    status declaration_status NOT NULL DEFAULT 'draft',
    entry_number VARCHAR(50),
    port_of_entry VARCHAR(10),
    declared_value_usd FLOAT,
    cif_value_usd FLOAT,
    fob_value_usd FLOAT,
    total_duty_usd FLOAT,
    total_tax_usd FLOAT,
    declaration_data JSONB,
    edi_content TEXT,
    inconsistencies JSONB,
    gpt_validation_notes TEXT,
    submitted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_declarations_shipment ON customs_declarations(shipment_id);

-- Denied Party Screenings
CREATE TABLE denied_party_screenings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    screened_by UUID NOT NULL,
    party_name VARCHAR(500) NOT NULL,
    party_type VARCHAR(50) NOT NULL,
    party_country VARCHAR(3),
    overall_result screening_result NOT NULL,
    matches JSONB,
    lists_checked JSONB,
    highest_score FLOAT NOT NULL DEFAULT 0.0,
    reviewed_by UUID,
    review_decision VARCHAR(20),
    review_notes TEXT,
    legal_hold_applied VARCHAR(5) NOT NULL DEFAULT 'false',
    whitelisted VARCHAR(5) NOT NULL DEFAULT 'false',
    whitelist_expiry TIMESTAMPTZ,
    screened_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_screenings_shipment ON denied_party_screenings(shipment_id);

-- Certificates of Origin
CREATE TABLE certificates_of_origin (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    created_by UUID NOT NULL,
    coo_format coo_format NOT NULL,
    origin_criterion origin_criterion NOT NULL,
    fta_agreement VARCHAR(50),
    exporter_name VARCHAR(255) NOT NULL,
    producer_name VARCHAR(255),
    importer_name VARCHAR(255) NOT NULL,
    country_of_origin VARCHAR(3) NOT NULL,
    origin_analysis TEXT,
    rvc_percentage FLOAT,
    rvc_calculation JSONB,
    preferential_duty_saving_usd FLOAT,
    document_content TEXT,
    is_certified VARCHAR(5) NOT NULL DEFAULT 'false',
    certified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_coo_shipment ON certificates_of_origin(shipment_id);

-- Trade Documents
CREATE TABLE trade_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL,
    document_type document_type NOT NULL,
    filename VARCHAR(255) NOT NULL,
    blob_url TEXT,
    ocr_extracted JSONB,
    ocr_confidence FLOAT,
    processing_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_documents_shipment ON trade_documents(shipment_id);

-- FTA Analyses
CREATE TABLE fta_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    line_item_id UUID REFERENCES shipment_line_items(id),
    origin_country VARCHAR(3) NOT NULL,
    destination_country VARCHAR(3) NOT NULL,
    hs_code VARCHAR(15) NOT NULL,
    applicable_ftas JSONB,
    recommended_fta VARCHAR(50),
    mfn_duty_rate FLOAT,
    preferential_duty_rate FLOAT,
    duty_saving_pct FLOAT,
    duty_saving_usd FLOAT,
    qualification_met VARCHAR(5) NOT NULL DEFAULT 'false',
    gpt_analysis TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_fta_shipment ON fta_analyses(shipment_id);

-- Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    shipment_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    details JSONB,
    ai_reasoning TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_shipment ON audit_logs(shipment_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- Auto-update triggers
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_shipments_updated BEFORE UPDATE ON shipments FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_products_updated BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_declarations_updated BEFORE UPDATE ON customs_declarations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
