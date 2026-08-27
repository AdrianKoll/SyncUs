BEGIN;

-- Converte os aliases históricos conhecidos para o vocabulário canônico.
UPDATE transactions
SET paid_by = CASE paid_by
    WHEN 'user1' THEN 'eu'
    WHEN 'user2' THEN 'parceira'
    WHEN 'partner' THEN 'parceira'
    WHEN 'both' THEN 'ambos'
    ELSE paid_by
END;

UPDATE transactions
SET split_type = CASE split_type
    WHEN '100_eu' THEN '100_user1'
    WHEN '100_parceira' THEN '100_user2'
    ELSE split_type
END;

-- O arredondamento ocorre uma única vez na migração do legado Float para
-- Numeric(12,2). Depois disso, a aplicação rejeita valores com mais de duas
-- casas decimais.
ALTER TABLE transactions
    ALTER COLUMN amount TYPE NUMERIC(12, 2)
    USING ROUND(amount::numeric, 2);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_transactions_amount_non_negative'
    ) THEN
        ALTER TABLE transactions
            ADD CONSTRAINT ck_transactions_amount_non_negative
            CHECK (amount >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_transactions_type_values'
    ) THEN
        ALTER TABLE transactions
            ADD CONSTRAINT ck_transactions_type_values
            CHECK (type IN ('entrada', 'saida'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_transactions_paid_by_values'
    ) THEN
        ALTER TABLE transactions
            ADD CONSTRAINT ck_transactions_paid_by_values
            CHECK (paid_by IN ('eu', 'parceira', 'ambos'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_transactions_split_type_values'
    ) THEN
        ALTER TABLE transactions
            ADD CONSTRAINT ck_transactions_split_type_values
            CHECK (split_type IN ('50/50', '100_user1', '100_user2', 'custom'));
    END IF;
END $$;

COMMIT;
