-- Table to store expenses
CREATE TABLE IF NOT EXISTS expenses (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('expense', 'income')),
    amount DECIMAL(10, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'CAD' CHECK (currency = 'CAD'),
    description TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('Food', 'Transportation', 'Entertainment', 'Services', 'Health', 'Shopping', 'Salary', 'Freelance', 'Business', 'Investment', 'Gift', 'Refund', 'Other')),
    date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE expenses ADD COLUMN IF NOT EXISTS transaction_type TEXT NOT NULL DEFAULT 'expense';
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'CAD';

-- Indexes to improve query performance
CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_expenses_transaction_type ON expenses(transaction_type);
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);

-- Enable Row Level Security (RLS)
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;

-- Policy to allow users to view their own expenses
CREATE POLICY "Users can view their own expenses" 
ON expenses FOR SELECT 
USING (true);

-- Policy to allow users to insert their own expenses
CREATE POLICY "Users can insert their own expenses" 
ON expenses FOR INSERT 
WITH CHECK (true);

-- Policy to allow users to update their own expenses
CREATE POLICY "Users can update their own expenses" 
ON expenses FOR UPDATE 
USING (true);

-- Policy to allow users to delete their own expenses
CREATE POLICY "Users can delete their own expenses" 
ON expenses FOR DELETE 
USING (true);

-- View for monthly summaries by category
CREATE OR REPLACE VIEW monthly_summary AS
SELECT 
    user_id,
    username,
    DATE_TRUNC('month', date) as month,
    transaction_type,
    category,
    COUNT(*) as transaction_count,
    SUM(amount) as category_total
FROM expenses
GROUP BY user_id, username, DATE_TRUNC('month', date), transaction_type, category
ORDER BY month DESC, category_total DESC;

-- View for totals by user
CREATE OR REPLACE VIEW user_totals AS
SELECT 
    user_id,
    username,
    DATE_TRUNC('month', date) as month,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END) as total_income,
    SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END) as total_expenses,
    SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE -amount END) as net_total
FROM expenses
GROUP BY user_id, username, DATE_TRUNC('month', date)
ORDER BY month DESC;
